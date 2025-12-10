@echo off
chcp 65001
echo Проверка и установка зависимостей...
for /f %%i in (Зависимости) do (
    echo Установка %%i...
    python -m pip install %%i
)
echo Запуск программы для клонирования и обновления репозиториев...
python main.py repos.txt
echo Готово! Проверьте папку ./repos и файл changes_results.json.
pause
