@echo off
chcp 65001
echo Запуск программы для клонирования и обновления репозиториев...
python main.py repos.txt
echo Готово! Проверьте папку ./repos и файл changes_results.json.
pause