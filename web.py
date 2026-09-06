"""Local web UI for ReposCloner (teacher's management tool).

Runs entirely on this machine — no hosting, no accounts. Launch with::

    streamlit run web.py

or via ``start-web.bat``.
"""

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import streamlit as st

from main import build_runtime, load_inventory
from reposcloner.config import is_debug_enabled, save_config
from reposcloner.git_operations import (
    clone_repo,
    delete_repo_checkout,
    get_commit_history,
    get_last_commit_summary,
    update_repo,
)
from reposcloner.i18n import AVAILABLE_LANGUAGES, get_lang, t
from reposcloner.report import build_dashboard_html
from reposcloner.repo_store import TrackedRepo, save_tracked, validate_repo_id
from reposcloner.search import search_in_repos


# --- runtime (loaded once per session) --------------------------------------

def get_runtime():
    if 'runtime' not in st.session_state:
        st.session_state['runtime'] = build_runtime()
    return st.session_state['runtime']


def refresh_inventory():
    runtime = get_runtime()
    config = runtime['config']
    items, ids, tracked_path, tracked = load_inventory(config, runtime['logger'])
    st.session_state['items'] = items
    st.session_state['all_ids'] = ids
    st.session_state['tracked_path'] = tracked_path
    st.session_state['tracked'] = tracked
    st.session_state.setdefault('scope', list(ids))
    # Drop scope entries that no longer exist.
    st.session_state['scope'] = [r for r in st.session_state['scope'] if r in ids]


def current_scope():
    return [r for r in st.session_state.get('scope', []) if r in st.session_state.get('all_ids', [])]


def run_parallel(repos, func, label):
    """Run func over repos in a thread pool, updating a progress bar."""
    config = get_runtime()['config']
    progress = st.progress(0, text=f"{label}…")
    results = []
    with ThreadPoolExecutor(max_workers=config['max_workers']) as pool:
        futures = {pool.submit(func, repo): repo for repo in repos}
        for i, future in enumerate(as_completed(futures), 1):
            results.append(future.result())
            progress.progress(i / len(repos), text=f"{label} ({i}/{len(repos)})")
    progress.empty()
    return results


# --- app ---------------------------------------------------------------------

st.set_page_config(page_title='ReposCloner', layout='wide')
refresh_inventory()

lang = get_lang(get_runtime()['config'])
choice = st.sidebar.radio(t('lang_label', lang), AVAILABLE_LANGUAGES,
                          index=AVAILABLE_LANGUAGES.index(lang), horizontal=True)
if choice != lang:
    cfg = get_runtime()['config']
    cfg['language'] = choice
    save_config(cfg)
    st.rerun()
lang = choice

# Hidden debug switch: ?debug=1 in the URL, REPOSCLONER_DEBUG=1, or config.
if st.query_params.get('debug', '') == '1':
    st.session_state['debug_url'] = True
debug = is_debug_enabled(get_runtime()['config']) or st.session_state.get('debug_url', False)
if debug:
    st.sidebar.caption(t('debug_on', lang))

st.title(t('app_title', lang))
items = st.session_state['items']
scope = current_scope()
st.caption(t('scope_caption', lang, a=len(scope), b=len(st.session_state['all_ids'])))

tab_repos, tab_commits, tab_search, tab_stats = st.tabs(
    [t('tab_repos', lang), t('tab_commits', lang),
     t('tab_search', lang), t('tab_stats', lang)])

# --- Repositories -------------------------------------------------------------
with tab_repos:
    notice = st.session_state.pop('notice', None)
    if notice:
        kind, text = notice
        (st.success if kind == 'success' else st.error)(text)
    for line in st.session_state.pop('notice_lines', []):
        st.error(line)

    col_list, col_actions = st.columns([3, 2])

    with col_list:
        st.subheader(t('inv_title', lang))
        st.dataframe(
            [{t('th_repo', lang): i.repo_id, t('th_group', lang): i.group,
              t('th_cloned', lang): i.cloned, t('th_enabled', lang): i.enabled}
             for i in items],
            use_container_width=True,
        )
        scope = st.multiselect(t('scope_label', lang), st.session_state['all_ids'],
                               default=scope, key='scope_box')
        st.session_state['scope'] = scope

        with st.expander(t('track_title', lang)):
            new_id = st.text_input('owner/repo')
            new_group = st.text_input(t('th_group', lang), value='default')
            if st.button(t('add_btn', lang)):
                try:
                    entry = TrackedRepo(id=validate_repo_id(new_id), group=new_group or 'default')
                    tracked = st.session_state['tracked'] + [entry]
                    save_tracked(st.session_state['tracked_path'], tracked)
                    st.session_state['notice'] = ('success', t('tracked_ok', lang, id=entry.id))
                    refresh_inventory()
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))

    with col_actions:
        st.subheader(t('ops_title', lang))
        shallow = st.checkbox(t('shallow_label', lang), key='shallow_clone') if debug else False
        if st.button(t('clone_btn', lang, n=len(scope)), disabled=not scope):
            clone_fn = (lambda repo: clone_repo(repo, depth=1)) if shallow else clone_repo
            results = run_parallel(scope, clone_fn, t('ops_title', lang))
            st.session_state['last_clone'] = results
            ok = sum(1 for r in results if r.get('status') in ('cloned', 'already_cloned'))
            err = sum(1 for r in results if r.get('status') == 'error')
            st.session_state['notice'] = (
                'success', t('clone_done', lang, ok=ok, err=err, total=len(results)))
            st.session_state['notice_lines'] = [
                f"{r['repo']}: {r.get('message')}" for r in results if r.get('status') == 'error']
            refresh_inventory()
            st.rerun()

        if st.button(t('update_btn', lang, n=len(scope)), disabled=not scope):
            results = run_parallel(scope, update_repo, t('ops_title', lang))
            st.session_state['last_update'] = results
            updated = sum(1 for r in results if r.get('status') in ('updated', 'updated_forced'))
            conflicts = [r for r in results if r.get('status') == 'conflict']
            errors = [r for r in results if r.get('status') == 'error']
            not_cloned = sum(1 for r in results if r.get('status') == 'not_cloned')
            new_total = sum(r.get('new_commits_count', 0) for r in results)
            text = t('update_done', lang, u=updated, n=new_total,
                     c=len(conflicts), e=len(errors))
            if not_cloned:
                text += ' — ' + t('not_cloned_hint', lang, k=not_cloned)
            st.session_state['notice'] = ('success', text)
            st.session_state['notice_lines'] = [
                f"{r['repo']}: {r.get('message')}" for r in errors]
            refresh_inventory()
            st.rerun()

        conflicts = [r for r in st.session_state.get('last_update', [])
                     if r.get('status') == 'conflict']
        if conflicts:
            st.warning(t('conflicts_warn', lang) + ' '
                       + ', '.join(r['repo'] for r in conflicts))
            if st.button(t('force_btn', lang)):
                config = get_runtime()['config']
                forced = run_parallel(
                    [r['repo'] for r in conflicts],
                    lambda repo: update_repo(repo, repos_dir=config['repos_dir'], force=True),
                    t('ops_title', lang),
                )
                st.session_state['last_update'] = forced
                st.session_state['notice'] = ('success', t('force_done', lang))
                refresh_inventory()
                st.rerun()

        with st.expander(t('danger_title', lang)):
            if not scope:
                st.info(t('scope_empty', lang))
            else:
                target = st.selectbox(t('danger_repo', lang), scope, key='danger_target')
                mode = st.radio(
                    t('danger_action', lang),
                    [t('danger_list_only', lang), t('danger_files', lang)],
                    key='danger_mode',
                )
                confirm = st.checkbox(t('danger_confirm', lang), key='danger_confirm')
                if st.button(t('remove_btn', lang), disabled=not confirm, key='danger_go'):
                    if mode == t('danger_files', lang):
                        result = delete_repo_checkout(target)
                        if result['status'] not in ('deleted', 'not_cloned'):
                            st.session_state['notice'] = (
                                'error', f"{target}: {result.get('message')}")
                            st.rerun()
                    tracked = [x for x in st.session_state['tracked'] if x.id != target]
                    save_tracked(st.session_state['tracked_path'], tracked)
                    st.session_state['scope'] = [
                        r for r in st.session_state['scope'] if r != target]
                    st.session_state['notice'] = ('success', t('removed', lang, id=target))
                    refresh_inventory()
                    st.rerun()

        if debug:
            with st.expander(t('debug_title', lang)):
                runtime = get_runtime()
                st.write({
                    t('dbg_cwd', lang): os.getcwd(),
                    t('dbg_repos', lang): os.path.abspath(runtime['config']['repos_dir']),
                    t('dbg_tracked', lang): st.session_state.get('tracked_path'),
                    t('dbg_scope', lang): current_scope(),
                })
                if 'last_clone' in st.session_state:
                    st.caption(t('dbg_last_clone', lang))
                    st.json(st.session_state['last_clone'])
                if 'last_update' in st.session_state:
                    st.caption(t('dbg_last_update', lang))
                    st.json(st.session_state['last_update'])
                if 'last_clone' not in st.session_state and 'last_update' not in st.session_state:
                    st.caption(t('dbg_no_ops', lang))

# --- Commits -------------------------------------------------------------------
with tab_commits:
    cloned = [i.repo_id for i in items if i.cloned]
    if not cloned:
        st.info(t('no_cloned', lang))
    else:
        repo = st.selectbox(t('commits_repo', lang), cloned)
        limit = st.slider(t('commits_limit', lang), 5, 200, 50)
        if st.button(t('commits_show', lang)):
            history = get_commit_history(repo, limit=limit)
            if history['status'] != 'ok':
                st.error(history.get('message', 'Unknown error'))
            else:
                st.dataframe(
                    [{t('th_hash', lang): c['short_hash'],
                      t('th_date', lang): c['date'][:16].replace('T', ' '),
                      t('th_author', lang): c['author'],
                      t('th_message', lang): c['message'].split('\n')[0][:100]}
                     for c in history['commits']],
                    use_container_width=True,
                )

# --- Search ----------------------------------------------------------------------
with tab_search:
    query = st.text_input(t('search_label', lang))
    if st.button(t('search_btn', lang), disabled=not query.strip()) and scope:
        with st.spinner(t('searching', lang)):
            results = search_in_repos(query.strip(), scope)
        if not results:
            st.info(t('search_none', lang, q=query))
        else:
            total = sum(r['count'] for r in results)
            st.success(t('search_found', lang, total=total, n=len(results)))
            for r in results:
                with st.expander(f"{r['repo']} ({r['count']})"):
                    st.dataframe(
                        [{t('th_hash', lang): m['hash'],
                          t('th_date', lang): m['date'][:16].replace('T', ' '),
                          t('th_author', lang): m['author'],
                          t('th_message', lang): m['message']}
                         for m in r['matches']],
                        use_container_width=True,
                    )

# --- Statistics --------------------------------------------------------------------
with tab_stats:
    from git import Repo as GitRepo

    config = get_runtime()['config']
    cloned_items = [i for i in items if i.cloned]
    total_size = 0
    total_commits = 0
    per_repo = []
    with st.spinner(t('stats_computing', lang)):
        for item in cloned_items:
            size = 0
            commits = 0
            try:
                for dirpath, _dirnames, filenames in os.walk(item.path):
                    for filename in filenames:
                        size += os.path.getsize(os.path.join(dirpath, filename))
                commits = sum(1 for _ in GitRepo(item.path).iter_commits())
            except Exception:
                pass
            total_size += size
            total_commits += commits
            per_repo.append({t('th_repo', lang): item.repo_id,
                             t('th_size', lang): round(size / (1024 * 1024), 2),
                             t('m_commits', lang): commits})
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(t('m_total', lang), len(items))
    c2.metric(t('m_cloned', lang), len(cloned_items))
    c3.metric(t('m_commits', lang), total_commits)
    c4.metric(t('m_size', lang), round(total_size / (1024 * 1024), 2))
    st.dataframe(per_repo, use_container_width=True)

    if st.button(t('export_btn', lang)):
        summaries = [get_last_commit_summary(i.repo_id) for i in items]
        page = build_dashboard_html(
            [{'repo_id': i.repo_id, 'group': i.group, 'cloned': i.cloned,
              'enabled': i.enabled} for i in items],
            summaries,
            {'total': len(items), 'cloned': len(cloned_items),
             'total_commits': total_commits,
             'total_size_mb': round(total_size / (1024 * 1024), 2)},
        )
        st.download_button(t('download_btn', lang), page,
                           file_name=f"dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
                           mime='text/html')
