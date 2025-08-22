# Log Sorter

**Тестовое задание по сортировке лог-файлов для WorkMate**
##Краткое описание
В скрипте реализована сортировка информациии из файлов с расширением log.

При вызове скрипта можно указать файл/файлы, через аргумент --files.

Через аргумент --report можно указать имя файла/отчёта.

Также дополнительно есть функция --date для указания даты за которую нужно вывести отчёт.

Через аргумент --createfile можно записать результат сразу в файл без вывода в консоль.  

**Примеры использования:**

python main.py --files example1.log --report average (1 файл)

<img width="924" height="147" alt="image" src="https://github.com/user-attachments/assets/e66fb03e-add2-4cb1-a176-0657ea089564" />  


python main.py --files example2.log, example1.log --report average (2 файла)

<img width="1011" height="191" alt="image" src="https://github.com/user-attachments/assets/91d32c96-ec86-420d-b1de-ed32e042d10a" />  


python main.py --files example2.log, example1.log --report average --date 2025-06-23 (2 файла и дата)

<img width="1113" height="193" alt="image" src="https://github.com/user-attachments/assets/ff2e2a58-3058-43f8-b553-f7ec775a51a5" />  


python main.py --files example2.log, example1.log --report average --date 2025-06-23 --createfile (2 файла и дата с выгрузкой в файл)
<img width="1124" height="53" alt="image" src="https://github.com/user-attachments/assets/06a786ff-a459-4e87-9893-3dbe1e877aa1" />  
<img width="584" height="223" alt="image" src="https://github.com/user-attachments/assets/8ba71583-cd62-4065-afd6-d216d6a0905f" />

  


**Отчёт о покрытии тестами: **  
<img width="1121" height="335" alt="image" src="https://github.com/user-attachments/assets/fba25946-c186-4e03-b785-bf30d7f6782c" />
