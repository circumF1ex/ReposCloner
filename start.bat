@echo off
chcp 65001
echo Проверка и установка зависимостей...
for /f %%i in (Зависимости) do (
    echo Установка %%i...
    py -m pip install %%i
)
echo Запуск программы для клонирования и обновления репозиториев...
py main.py repos.txt
echo Готово! Проверьте папку ./repos и файл changes_results_*.json.
pause
