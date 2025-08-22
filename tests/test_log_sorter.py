import pytest
import os
import datetime
import sys
from unittest.mock import patch
import argparse
import re

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, os.pardir))

if project_root not in sys.path:
    sys.path.insert(0, project_root)



from main import (
    get_unique_filename,
    parse_log_files,
    filter_log_entries_by_date,
    analyze_url_metrics,
    print_url_metrics_table,
    main
)



def test_get_unique_filename_no_conflict(mocker):
    mocker.patch('os.path.exists', return_value=False)
    assert get_unique_filename("report_name") == "report_name.txt"
    assert os.path.exists.call_count == 1


def test_get_unique_filename_one_conflict(mocker):
    mocker.patch('os.path.exists', side_effect=[True, False])
    assert get_unique_filename("report_name") == "report_name_1.txt"
    assert os.path.exists.call_count == 2


def test_get_unique_filename_multiple_conflicts(mocker):
    mocker.patch('os.path.exists', side_effect=[True, True, False])
    assert get_unique_filename("report_name") == "report_name_2.txt"
    assert os.path.exists.call_count == 3


def test_get_unique_filename_with_different_extension(mocker):
    mocker.patch('os.path.exists', return_value=False)
    assert get_unique_filename("data", extension=".csv") == "data.csv"



def test_parse_log_files_empty_list():
    assert parse_log_files([]) == []


def test_parse_log_files_non_existent_file(mocker, capsys):
    mocker.patch('os.path.exists', return_value=False)
    mocker.patch('os.path.isfile', return_value=False)
    result = parse_log_files(["non_existent.log"])
    assert result == []
    captured = capsys.readouterr()
    assert "Файл 'non_existent.log' не найден" in captured.err


def test_parse_log_files_not_a_file(mocker, capsys):
    mocker.patch('os.path.exists', return_value=True)
    mocker.patch('os.path.isfile', return_value=False)
    result = parse_log_files(["dir_not_file.log"])
    assert result == []
    captured = capsys.readouterr()
    assert "Путь 'dir_not_file.log' не является файлом" in captured.err


def test_parse_log_files_valid_json_lines(tmp_path):
    file_path = tmp_path / "test.log"
    file_path.write_text(
        '{"a": 1, "url": "/test1", "response_time": 10}\n{"b": 2, "url": "/test2", "response_time": 20}')
    expected = [{"a": 1, "url": "/test1", "response_time": 10}, {"b": 2, "url": "/test2", "response_time": 20}]
    assert parse_log_files([str(file_path)]) == expected


def test_parse_log_files_with_empty_lines(tmp_path):
    file_path = tmp_path / "test.log"
    file_path.write_text('{"a": 1}\n\n{"b": 2}')
    expected = [{"a": 1}, {"b": 2}]
    assert parse_log_files([str(file_path)]) == expected


def test_parse_log_files_with_invalid_json_line(tmp_path, capsys):
    file_path = tmp_path / "test.log"
    file_path.write_text('{"a": 1}\nInvalid JSON\n{"b": 2}')
    expected = [{"a": 1}, {"b": 2}]
    result = parse_log_files([str(file_path)])
    assert result == expected
    captured = capsys.readouterr()
    assert "Не удалось распарсить строку как JSON в" in captured.err
    assert "Invalid JSON" in captured.err


def test_parse_log_files_io_error(mocker, capsys):
    mocker.patch('os.path.exists', return_value=True)
    mocker.patch('os.path.isfile', return_value=True)
    mocker.patch('builtins.open', side_effect=IOError("Permission denied"))
    result = parse_log_files(["locked.log"])
    assert result == []
    captured = capsys.readouterr()
    assert "Ошибка при чтении файла 'locked.log': Permission denied" in captured.err



def test_filter_log_entries_by_date_no_specific_date():
    logs = [{"@timestamp": "2023-01-01"}, {"@timestamp": "2023-01-02"}]
    assert filter_log_entries_by_date(logs, None) == logs


def test_filter_log_entries_by_date_matching_iso_format():
    logs = [
        {"@timestamp": "2023-01-01T10:00:00Z", "data": "entry1"},
        {"@timestamp": "2023-01-02T11:00:00Z", "data": "entry2"}
    ]
    expected = [{"@timestamp": "2023-01-01T10:00:00Z", "data": "entry1"}]
    assert filter_log_entries_by_date(logs, datetime.date(2023, 1, 1)) == expected


def test_filter_log_entries_by_date_matching_ymd_format():
    logs = [
        {"@timestamp": "2023-01-01 10:00:00", "data": "entry1"},
        {"@timestamp": "2023-01-02 11:00:00", "data": "entry2"}
    ]
    expected = [{"@timestamp": "2023-01-01 10:00:00", "data": "entry1"}]
    assert filter_log_entries_by_date(logs, datetime.date(2023, 1, 1)) == expected


def test_filter_log_entries_by_date_non_matching_date():
    logs = [
        {"@timestamp": "2023-01-01T10:00:00Z"},
        {"@timestamp": "2023-01-02T11:00:00Z"}
    ]
    assert filter_log_entries_by_date(logs, datetime.date(2023, 1, 3)) == []


def test_filter_log_entries_by_date_missing_timestamp_field():
    logs = [
        {"data": "entry1"},
        {"@timestamp": "2023-01-01T10:00:00Z", "data": "entry2"}
    ]
    expected = [{"@timestamp": "2023-01-01T10:00:00Z", "data": "entry2"}]
    assert filter_log_entries_by_date(logs, datetime.date(2023, 1, 1)) == expected


def test_filter_log_entries_by_date_invalid_timestamp_format():
    logs = [
        {"@timestamp": "invalid-date-format"},
        {"@timestamp": "2023-01-01T10:00:00Z", "data": "entry2"}
    ]
    expected = [{"@timestamp": "2023-01-01T10:00:00Z", "data": "entry2"}]
    assert filter_log_entries_by_date(logs, datetime.date(2023, 1, 1)) == expected


def test_filter_log_entries_by_date_custom_timestamp_field():
    logs = [
        {"event_time": "2023-01-01T10:00:00Z", "data": "entry1"},
        {"event_time": "2023-01-02T11:00:00Z", "data": "entry2"}
    ]
    expected = [{"event_time": "2023-01-01T10:00:00Z", "data": "entry1"}]
    assert filter_log_entries_by_date(logs, datetime.date(2023, 1, 1), timestamp_field_name='event_time') == expected



def test_analyze_url_metrics_empty_logs():
    assert analyze_url_metrics([]) == {}


def test_analyze_url_metrics_basic_data():
    logs = [
        {"url": "/api/users", "response_time": 100},
        {"url": "/api/products", "response_time": 200},
        {"url": "/api/users", "response_time": 150},
    ]
    expected = {
        "/api/users": {"total": 2, "avg_time": 125.0},
        "/api/products": {"total": 1, "avg_time": 200.0}
    }
    result = analyze_url_metrics(logs)
    assert result["/api/users"]["avg_time"] == pytest.approx(125.0)
    assert result["/api/products"]["avg_time"] == pytest.approx(200.0)
    assert result["/api/users"]["total"] == 2
    assert result["/api/products"]["total"] == 1


def test_analyze_url_metrics_missing_fields():
    logs = [
        {"url": "/api/users", "response_time": 100},
        {"message": "no url or response_time"},
        {"url": "/api/products"},
        {"response_time": 50},
        {"url": "/api/users", "response_time": "invalid_time"},
    ]
    expected = {
        "/api/users": {"total": 1, "avg_time": 100.0}
    }
    result = analyze_url_metrics(logs)
    assert result["/api/users"]["avg_time"] == pytest.approx(100.0)
    assert result["/api/users"]["total"] == 1
    assert len(result) == 1


def test_analyze_url_metrics_zero_response_time():
    logs = [
        {"url": "/api/test", "response_time": 0},
        {"url": "/api/test", "response_time": 0},
    ]
    expected = {
        "/api/test": {"total": 2, "avg_time": 0.0}
    }
    assert analyze_url_metrics(logs) == expected


def test_analyze_url_metrics_various_data_types():
    logs = [
        {"url": "/api/float", "response_time": 10.5},
        {"url": "/api/float", "response_time": 20.5},
        {"url": "/api/int", "response_time": 100},
    ]
    expected = {
        "/api/float": {"total": 2, "avg_time": 15.5},
        "/api/int": {"total": 1, "avg_time": 100.0},
    }
    result = analyze_url_metrics(logs)
    assert result["/api/float"]["avg_time"] == pytest.approx(15.5)
    assert result["/api/int"]["avg_time"] == pytest.approx(100.0)



def test_print_url_metrics_table_empty_data(capsys):
    print_url_metrics_table({})
    captured = capsys.readouterr()
    assert "Нет данных для отображения метрик." in captured.out
    assert captured.err == ""


def test_print_url_metrics_table_single_entry(capsys):
    metrics_data = {
        "/api/test": {"total": 1, "avg_time": 123.4567}
    }
    print_url_metrics_table(metrics_data)
    captured = capsys.readouterr()
    assert "handler" in captured.out
    assert "total" in captured.out
    assert "avg_response_time" in captured.out
    assert re.search(r"^\s*0\s+/api/test\s+1\s+123\.457$", captured.out, re.MULTILINE) is not None
    assert captured.err == ""


def test_print_url_metrics_table_multiple_entries_and_sorting(capsys):
    metrics_data = {
        "/api/z_low_freq": {"total": 1, "avg_time": 10.0},
        "/api/a_high_freq": {"total": 5, "avg_time": 20.0},
        "/api/m_med_freq": {"total": 3, "avg_time": 30.0},
    }
    print_url_metrics_table(metrics_data)
    captured = capsys.readouterr()

    assert "handler" in captured.out
    assert re.search(r"^\s*0\s+/api/a_high_freq\s+5\s+20(\.000)?$", captured.out, re.MULTILINE) is not None
    assert re.search(r"^\s*1\s+/api/m_med_freq\s+3\s+30(\.000)?$", captured.out, re.MULTILINE) is not None
    assert re.search(r"^\s*2\s+/api/z_low_freq\s+1\s+10(\.000)?$", captured.out, re.MULTILINE) is not None
    assert captured.err == ""


def test_print_url_metrics_table_url_truncation(capsys):
    metrics_data = {
        "/api/this/is/a/very/long/url/that/should/be/truncated": {"total": 1, "avg_time": 100.0},
        "/short": {"total": 2, "avg_time": 50.0}
    }
    print_url_metrics_table(metrics_data)
    captured = capsys.readouterr()

    assert "handler" in captured.out
    assert re.search(r"^\s*0\s+/short\s+2\s+50(\.000)?$", captured.out, re.MULTILINE) is not None
    assert re.search(r"^\s*1\s+/api/this/is/a/very/long/ur...\s+1\s+100(\.000)?$", captured.out, re.MULTILINE) is not None
    assert captured.err == ""


@patch('sys.exit')
@patch('argparse.ArgumentParser.parse_args')
def test_main_no_files_exits(mock_parse_args, mock_sys_exit, capsys):
    mock_parse_args.return_value = argparse.Namespace(
        files=None,
        report="TestReport",
        date=None,
        createfile=False
    )
    main()
    mock_sys_exit.assert_called_once_with(1)
    captured = capsys.readouterr()
    assert "Ошибка: Необходимо указать файлы для обработки с помощью --files." in captured.err


@patch('sys.exit')
@patch('argparse.ArgumentParser.parse_args')
def test_main_invalid_date_exits(mock_parse_args, mock_sys_exit, capsys):
    mock_parse_args.return_value = argparse.Namespace(
        files=["dummy.log"],
        report="TestReport",
        date="bad-date-format",
        createfile=False
    )
    main()
    mock_sys_exit.assert_called_once_with(1)
    captured = capsys.readouterr()
    assert "Ошибка: Неверный формат даты 'bad-date-format'." in captured.err


@patch('sys.exit')
@patch('argparse.ArgumentParser.parse_args')
def test_main_no_valid_logs_exits(mock_parse_args, mock_sys_exit, mocker, capsys, tmp_path):
    log_file = tmp_path / "empty.log"
    log_file.write_text("")

    mock_parse_args.return_value = argparse.Namespace(
        files=[str(log_file)],
        report="TestReport",
        date=None,
        createfile=False
    )
    mocker.patch('main.os.path.exists', return_value=True)
    mocker.patch('main.os.path.isfile', return_value=True)

    main()
    mock_sys_exit.assert_called_once_with(1)
    captured = capsys.readouterr()
    assert "Не удалось прочитать ни одной валидной записи лога из указанных файлов." in captured.err


@patch('sys.exit')
@patch('argparse.ArgumentParser.parse_args')
def test_main_no_matching_date_exits_gracefully(mock_parse_args, mock_sys_exit, mocker, capsys, tmp_path):
    log_file = tmp_path / "test.log"
    log_file.write_text('{"url": "/a", "response_time": 100, "@timestamp": "2023-01-01T10:00:00Z"}\n')

    mock_parse_args.return_value = argparse.Namespace(
        files=[str(log_file)],
        report="TestReport",
        date="2023-01-02",
        createfile=False
    )
    mocker.patch('main.os.path.exists', return_value=True)
    mocker.patch('main.os.path.isfile', return_value=True)

    main()
    mock_sys_exit.assert_called_once_with(0)
    captured = capsys.readouterr()
    assert "Нет записей лога, соответствующих дате 2023-01-02." in captured.err


@patch('sys.exit')
@patch('argparse.ArgumentParser.parse_args')
def test_main_successful_run_console_output(mock_parse_args, mock_sys_exit, mocker, capsys, tmp_path):
    log_file = tmp_path / "test.log"
    log_file.write_text('{"url": "/a", "response_time": 100, "@timestamp": "2023-01-01T10:00:00Z"}\n'
                        '{"url": "/b", "response_time": 200, "@timestamp": "2023-01-01T10:00:00Z"}\n'
                        '{"url": "/a", "response_time": 150, "@timestamp": "2023-01-01T10:00:00Z"}\n')

    mock_parse_args.return_value = argparse.Namespace(
        files=[str(log_file)],
        report="MyReport",
        date="2023-01-01",
        createfile=False
    )
    mocker.patch('main.os.path.exists', return_value=True)
    mocker.patch('main.os.path.isfile', return_value=True)

    main()
    mock_sys_exit.assert_not_called()

    captured = capsys.readouterr()
    assert "handler" in captured.out
    assert "total" in captured.out
    assert "avg_response_time" in captured.out
    assert re.search(r"^\s*0\s+/a\s+2\s+125(\.000)?$", captured.out, re.MULTILINE) is not None
    assert re.search(r"^\s*1\s+/b\s+1\s+200(\.000)?$", captured.out, re.MULTILINE) is not None
    assert captured.err == ""


@patch('sys.exit')
@patch('argparse.ArgumentParser.parse_args')
def test_main_createfile_successful(mock_parse_args, mock_sys_exit, mocker, capsys, tmp_path):
    log_file_path = tmp_path / "test.log"
    log_file_path.write_text('{"url": "/x", "response_time": 50, "@timestamp": "2023-01-01T10:00:00Z"}\n')

    mock_parse_args.return_value = argparse.Namespace(
        files=[str(log_file_path)],
        report="OutputReport",
        date="2023-01-01",
        createfile=True
    )

    expected_parsed_logs = [{"url": "/x", "response_time": 50, "@timestamp": "2023-01-01T10:00:00Z"}]
    mocker.patch('main.parse_log_files', return_value=expected_parsed_logs)

    mocker.patch('main.os.path.exists', side_effect=[True, False])

    mock_open_func = mocker.patch('builtins.open', mocker.mock_open())

    main()
    mock_sys_exit.assert_not_called()

    captured = capsys.readouterr()
    expected_filename_in_output = f"OutputReport_2023-01-01_1.txt"
    assert f"Вывод успешно записан в файл: {expected_filename_in_output}" in captured.out

    file_open_arg = mock_open_func.call_args[0][0]
    assert file_open_arg.endswith(expected_filename_in_output)

    mock_open_func().write.assert_called_once()
    written_content = mock_open_func().write.call_args[0][0]
    assert "handler" in written_content
    assert "/x" in written_content
    assert "50" in written_content
    assert captured.err == ""

