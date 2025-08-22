import os
import json
import tabulate
import argparse
import sys
import io
import datetime


def get_unique_filename(base_name, extension=".txt"):
    filename = f"{base_name}{extension}"
    counter = 0
    while os.path.exists(filename):
        counter += 1
        filename = f"{base_name}_{counter}{extension}"
    return filename


def parse_log_files(filepaths):
    all_parsed_logs = []
    for filepath in filepaths:
        if not os.path.exists(filepath):
            print(f"Внимание: Файл '{filepath}' не найден, пропускаем.", file=sys.stderr)
            continue
        if not os.path.isfile(filepath):
            print(f"Внимание: Путь '{filepath}' не является файлом, пропускаем.", file=sys.stderr)
            continue

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        log_entry = json.loads(line)
                        all_parsed_logs.append(log_entry)
                    except json.JSONDecodeError:
                        print(f"Внимание: Не удалось распарсить строку как JSON в '{filepath}': {line}",
                              file=sys.stderr)
                        continue
        except IOError as e:
            print(f"Ошибка при чтении файла '{filepath}': {e}", file=sys.stderr)
            continue
    return all_parsed_logs


def filter_log_entries_by_date(log_entries, specific_date, timestamp_field_name='@timestamp'):
    if not specific_date:
        return log_entries

    filtered_entries = []
    for entry in log_entries:
        timestamp_str = entry.get(timestamp_field_name)
        if timestamp_str:
            try:
                log_date = None
                try:
                    log_datetime = datetime.datetime.fromisoformat(timestamp_str)
                    log_date = log_datetime.date()
                except ValueError:
                    try:
                        log_date = datetime.datetime.strptime(timestamp_str.split(' ')[0], '%Y-%m-%d').date()
                    except ValueError:
                        pass

                if log_date and log_date == specific_date:
                    filtered_entries.append(entry)
            except Exception as e:
                pass
    return filtered_entries


def analyze_url_metrics(log_entries):
    url_data = {}

    for entry in log_entries:
        url = entry.get('url')
        response_time = entry.get('response_time')

        if url and isinstance(response_time, (int, float)):
            if url not in url_data:
                url_data[url] = {
                    'total_requests': 0,
                    'sum_response_time': 0
                }

            url_data[url]['total_requests'] += 1
            url_data[url]['sum_response_time'] += response_time

    final_metrics = {}
    for url, data in url_data.items():
        total = data['total_requests']
        sum_time = data['sum_response_time']

        avg_time = sum_time / total if total > 0 else 0

        final_metrics[url] = {
            'total': total,
            'avg_time': avg_time
        }

    return final_metrics


def print_url_metrics_table(url_metrics_data):
    if not url_metrics_data:
        print("Нет данных для отображения метрик.")
        return

    table_data = []
    max_url_len = 30

    sorted_metrics = sorted(url_metrics_data.items(), key=lambda item: item[1]['total'], reverse=True)

    for url, metrics in sorted_metrics:
        display_url = url
        if len(url) > max_url_len:
            display_url = url[:max_url_len - 3] + "..."

        table_data.append([
            display_url,
            metrics['total'],
            f"{metrics['avg_time']:.3f}" 
        ])

    headers = ["handler", "total", "avg_response_time"]

    print(tabulate.tabulate(
        table_data,
        headers=headers,
        tablefmt="simple",
        showindex=True,
        numalign="right",
        stralign="left"
    ))


def main():
    parser = argparse.ArgumentParser(
        description="Анализирует лог-файлы в формате JSON Lines и выводит метрики по URL."
    )

    parser.add_argument(
        '--files',
        nargs='+',
        help='Путь к одному или нескольким лог-файлам JSON Lines.'
    )

    parser.add_argument(
        "--report",
        type=str,
        required=True,
        help="Базовое название для файла отчета (без расширения) или для заголовка консольного вывода. "
             "Пример: 'ОтчетПоЗапросам'."
    )

    parser.add_argument(
        "--date",
        type=str,
        help="Конкретная дата для фильтрации данных в формате YYYY-MM-DD. "
             "Пример: 2025-06-22. Ожидается наличие поля '@timestamp' (или другого) в логах."
    )

    parser.add_argument(
        "--createfile",
        action="store_true",
        help="Если указан, весь основной вывод скрипта будет записан в файл с именем из --report. "
             "Если файл с таким именем уже существует, будет добавлен числовой суффикс."
             "Если не указан, вывод будет напечатан в консоль. Ошибки всегда выводятся в stderr."
    )

    args = parser.parse_args()

    original_stdout = sys.stdout
    output_buffer = io.StringIO()

    if args.createfile:
        sys.stdout = output_buffer

    specific_date = None
    if args.date:
        try:
            specific_date = datetime.datetime.strptime(args.date, '%Y-%m-%d').date()
        except ValueError:
            print(f"Ошибка: Неверный формат даты '{args.date}'. Ожидается YYYY-MM-DD.", file=sys.stderr)
            sys.exit(1)
            return


    if not args.files:
        print("Ошибка: Необходимо указать файлы для обработки с помощью --files.", file=sys.stderr)
        sys.exit(1)
        return

    all_log_entries = parse_log_files(args.files)

    if not all_log_entries:
        print("Не удалось прочитать ни одной валидной записи лога из указанных файлов.", file=sys.stderr)
        if args.createfile:
            sys.stdout = original_stdout
        sys.exit(1)
        return

    if specific_date:
        filtered_entries = filter_log_entries_by_date(all_log_entries, specific_date)
        if not filtered_entries:
            print(f"Нет записей лога, соответствующих дате {specific_date.strftime('%Y-%m-%d')}.", file=sys.stderr)
            if args.createfile:
                sys.stdout = original_stdout
            sys.exit(0)
            return
        all_log_entries = filtered_entries

    url_metrics = analyze_url_metrics(all_log_entries)

    print_url_metrics_table(url_metrics)

    if args.createfile:
        sys.stdout = original_stdout

        report_base_name = args.report
        if specific_date:
            report_base_name += f"_{specific_date.strftime('%Y-%m-%d')}"

        log_filename = get_unique_filename(report_base_name, extension=".txt")

        try:
            with open(log_filename, 'w', encoding='utf-8') as f:
                f.write(output_buffer.getvalue())
            print(f"Вывод успешно записан в файл: {log_filename}")
        except IOError as e:
            print(f"Ошибка при записи в файл {log_filename}: {e}", file=sys.stderr)
    else:
        pass


if __name__ == "__main__":
    main()