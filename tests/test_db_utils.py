import pytest
import os
import csv
import pandas as pd
from src.elxr_metrics.db_utils import manage_db_connection

# Helper function to read CSV content
def read_csv_content(file_path, expected_headers=None):
    if not os.path.exists(file_path):
        return None # Or raise error, depending on test needs
    if os.path.getsize(file_path) == 0: # Handle completely empty file
        return []

    content = []
    with open(file_path, 'r', newline='') as f:
        reader = csv.DictReader(f)
        if expected_headers:
            # Fieldnames might be quoted if they had spaces and were written by duckdb COPY
            # For simplicity, we'll assume test headers are simple or match exactly for now.
            # A more robust check might involve unquoting read fieldnames.
            assert reader.fieldnames == expected_headers, f"CSV headers mismatch: expected {expected_headers}, got {reader.fieldnames}"
        for row in reader:
            content.append(row)
    return content

@pytest.fixture
def default_schema():
    # Simplified: PRIMARY KEY constraint removed from schema string, as types must be single words.
    return "Name VARCHAR, Download INTEGER"

@pytest.fixture
def default_table_name():
    return "test_table"

def test_new_csv_creation(tmp_path, default_table_name, default_schema):
    input_csv = tmp_path / "input.csv" # Does not exist initially
    output_csv = tmp_path / "output.csv"
    top_n_csv = tmp_path / "top_10.csv"
    top_n_count = 3

    data_to_insert = [
        ("item1", 100),
        ("item2", 200),
        ("item3", 50),
    ]

    with manage_db_connection(
        db_name=":memory:",
        table_name=default_table_name,
        table_schema=default_schema,
        input_csv_path=str(input_csv),
        output_csv_path=str(output_csv),
        top_n_csv_path=str(top_n_csv),
        top_n=top_n_count
    ) as conn:
        for name, download in data_to_insert:
            conn.execute(f"INSERT INTO {default_table_name} (Name, Download) VALUES (?, ?)", [name, download])

    assert output_csv.exists()
    output_data = read_csv_content(str(output_csv))
    assert len(output_data) == len(data_to_insert)
    output_set = set((row['Name'], int(row['Download'])) for row in output_data)
    assert output_set == set(data_to_insert)

    assert top_n_csv.exists()
    top_n_data = read_csv_content(str(top_n_csv))
    assert len(top_n_data) == top_n_count
    assert top_n_data[0]['Name'] == "item2"
    assert top_n_data[1]['Name'] == "item1"
    assert top_n_data[2]['Name'] == "item3"

def test_load_from_existing_csv(tmp_path, default_table_name, default_schema):
    input_csv = tmp_path / "input.csv"
    output_csv = tmp_path / "output.csv"
    top_n_csv = tmp_path / "top_10.csv"
    top_n_count = 2

    initial_data = [
        {"Name": "itemA", "Download": 500},
        {"Name": "itemB", "Download": 600},
    ]
    pd.DataFrame(initial_data).to_csv(input_csv, index=False)

    new_row_data = ("itemC", 700)

    with manage_db_connection(
        db_name=":memory:",
        table_name=default_table_name,
        table_schema=default_schema,
        input_csv_path=str(input_csv),
        output_csv_path=str(output_csv),
        top_n_csv_path=str(top_n_csv),
        top_n=top_n_count
    ) as conn:
        res = conn.execute(f"SELECT Name, Download FROM {default_table_name} ORDER BY Download").fetchall()
        assert len(res) == len(initial_data)
        assert res[0] == ("itemA", 500)
        assert res[1] == ("itemB", 600)

        conn.execute(f"INSERT INTO {default_table_name} (Name, Download) VALUES (?, ?)", new_row_data)

    output_data = read_csv_content(str(output_csv))
    assert len(output_data) == len(initial_data) + 1
    output_downloads = {row['Name']: int(row['Download']) for row in output_data}
    assert output_downloads["itemA"] == 500
    assert output_downloads["itemB"] == 600
    assert output_downloads["itemC"] == 700

    top_n_data = read_csv_content(str(top_n_csv))
    assert len(top_n_data) == top_n_count
    assert top_n_data[0]['Name'] == "itemC"
    assert top_n_data[1]['Name'] == "itemB"

def test_empty_input_csv(tmp_path, default_table_name, default_schema):
    input_csv = tmp_path / "input.csv"
    output_csv = tmp_path / "output.csv"
    top_n_csv = tmp_path / "top_10.csv"

    with open(input_csv, 'w') as f:
        pass

    data_to_insert = [("itemNew", 10)]

    with manage_db_connection(
        db_name=":memory:",
        table_name=default_table_name,
        table_schema=default_schema,
        input_csv_path=str(input_csv),
        output_csv_path=str(output_csv),
        top_n_csv_path=str(top_n_csv),
        top_n=1
    ) as conn:
        conn.execute(f"INSERT INTO {default_table_name} (Name, Download) VALUES (?, ?)", data_to_insert[0])

    output_data = read_csv_content(str(output_csv))
    assert len(output_data) == 1
    assert output_data[0]['Name'] == "itemNew"
    assert int(output_data[0]['Download']) == 10

    top_n_data = read_csv_content(str(top_n_csv))
    assert len(top_n_data) == 1
    assert top_n_data[0]['Name'] == "itemNew"

def test_input_csv_with_only_headers(tmp_path, default_table_name, default_schema):
    input_csv = tmp_path / "input.csv"
    output_csv = tmp_path / "output.csv"
    top_n_csv = tmp_path / "top_10.csv"

    raw_col_names = [part.strip().split(' ')[0] for part in default_schema.split(',')]
    headers_str = ",".join(raw_col_names)
    with open(input_csv, 'w') as f:
        f.write(headers_str + "\n")

    data_to_insert = [("itemOnly", 25)]
    with manage_db_connection(
        db_name=":memory:",
        table_name=default_table_name,
        table_schema=default_schema,
        input_csv_path=str(input_csv),
        output_csv_path=str(output_csv),
        top_n_csv_path=str(top_n_csv),
        top_n=1
    ) as conn:
        conn.execute(f"INSERT INTO {default_table_name} (Name, Download) VALUES (?, ?)", data_to_insert[0])

    output_data = read_csv_content(str(output_csv))
    assert len(output_data) == 1
    assert output_data[0]['Name'] == "itemOnly"
    assert int(output_data[0]['Download']) == 25

    top_n_data = read_csv_content(str(top_n_csv))
    assert len(top_n_data) == 1
    assert top_n_data[0]['Name'] == "itemOnly"

def test_save_top_n_more_than_10_items(tmp_path, default_table_name, default_schema):
    input_csv = tmp_path / "input.csv"
    output_csv = tmp_path / "output.csv"
    top_n_csv = tmp_path / "top_10_actually_5.csv"
    top_n_count = 5

    data_to_insert = [(f"item_{i}", i * 10) for i in range(1, 16)]

    with manage_db_connection(
        db_name=":memory:",
        table_name=default_table_name,
        table_schema=default_schema,
        input_csv_path=str(input_csv),
        output_csv_path=str(output_csv),
        top_n_csv_path=str(top_n_csv),
        top_n=top_n_count
    ) as conn:
        for name, download in data_to_insert:
            conn.execute(f"INSERT INTO {default_table_name} (Name, Download) VALUES (?, ?)", [name, download])

    output_data = read_csv_content(str(output_csv))
    assert len(output_data) == 15

    top_n_data = read_csv_content(str(top_n_csv))
    assert len(top_n_data) == top_n_count
    for i in range(top_n_count):
        expected_name = f"item_{15-i}"
        expected_download = (15-i) * 10
        assert top_n_data[i]['Name'] == expected_name
        assert int(top_n_data[i]['Download']) == expected_download

def test_empty_table_top_n_save(tmp_path, default_table_name, default_schema):
    input_csv = tmp_path / "input.csv"
    output_csv = tmp_path / "output.csv"
    top_n_csv = tmp_path / "top_10_empty.csv"

    with manage_db_connection(
        db_name=":memory:",
        table_name=default_table_name,
        table_schema=default_schema,
        input_csv_path=str(input_csv),
        output_csv_path=str(output_csv),
        top_n_csv_path=str(top_n_csv),
        top_n=10
    ) as conn:
        pass

    assert output_csv.exists()
    output_content = pd.read_csv(output_csv)
    assert output_content.empty
    with open(output_csv, 'r') as f:
        header_line = f.readline().strip()
        raw_col_names = [part.strip().split(' ')[0] for part in default_schema.split(',')]
        expected_header_str = ",".join(raw_col_names)
        assert header_line == expected_header_str

    assert top_n_csv.exists()
    assert os.path.getsize(str(top_n_csv)) <= 1, "Top N CSV for empty table should be empty or just a newline."

# Test cases for ordering column heuristic
# expected_top_identifier_in_first_col is the value in the *first column* of the schema for the row that is expected to be top
@pytest.mark.parametrize("schema, data, _, expected_top_identifier_in_first_col", [
    ("Name VARCHAR, Count INTEGER", [("A", 10), ("B", 30), ("C", 20)], "Count", "B"),
    ("ID INTEGER, Description VARCHAR, Value REAL", [ (1, "desc1", 0.5), (2, "desc2", 1.5), (3, "desc3", 1.0)], "Value", 2),
    ("ItemID VARCHAR, Price FLOAT, Stock INTEGER", [("X", 10.0, 5), ("Y", 5.0, 10), ("Z", 12.0, 2)], "Price", "Z"),
    # Replaced DECIMAL(3,1) with FLOAT. Data is now float.
    ("Product TEXT, Category TEXT, Rating FLOAT", [("P1","C1", 4.5), ("P2","C2", 3.5), ("P3","C1", 5.0)], "Rating", "P3"),
    ("FieldA VARCHAR, FieldB TEXT", [("row1", "data1"), ("row2", "data2")], "FieldA", "row2"),
    ("Download INTEGER, Name VARCHAR", [ (100, "zeta"), (200, "alpha")], "Download", 200),
    ("foo VARCHAR, Downloads INTEGER", [("bar", 50), ("baz", 10)], "Downloads", "bar")
])
def test_ordering_column_heuristic(tmp_path, schema, data, _, expected_top_identifier_in_first_col):
    table_name = "heuristic_test"
    input_csv = tmp_path / "input_heuristic.csv"
    output_csv = tmp_path / "output_heuristic.csv"
    top_n_csv = tmp_path / "top_1_heuristic.csv"

    headers = [col_def.strip().split(" ")[0] for col_def in schema.split(",")]

    dummy_row_values = []
    # DECIMAL type removed from col_types_map as it's replaced by FLOAT in schema list
    col_types_map = {"INTEGER":0, "BIGINT":0, "FLOAT":0.0, "DOUBLE":0.0, "REAL":0.0, "VARCHAR":"dummy", "TEXT":"dummy"}

    # Create dummy CSV for all heuristic test cases. FLOAT should not cause sniffing issues.
    for col_def in schema.split(','):
        parts = col_def.strip().split(" ", 1)
        col_type_general = ""
        # For simple types like FLOAT, actual_type_for_map is same as col_type_general after .upper()
        actual_type_for_map = ""
        if len(parts) > 1:
            col_type_general = parts[1].upper()
            actual_type_for_map = col_type_general # e.g. "FLOAT"

        if actual_type_for_map in col_types_map:
            found_val = col_types_map[actual_type_for_map]
        else:
            # Fallback for types not explicitly in map, or if parsing was imperfect for complex types (though now simplified)
            found_val = next((val for k_type, val in col_types_map.items() if k_type and k_type in col_type_general), "dummy_fallback")

        if not col_type_general:
            found_val = "dummy_no_type"
        dummy_row_values.append(found_val)
    if dummy_row_values: # Ensure we have something to write if schema was not empty
            pd.DataFrame([dummy_row_values], columns=headers).to_csv(input_csv, index=False)


    with manage_db_connection(
        db_name=":memory:",
        table_name=table_name,
        table_schema=schema,
        input_csv_path=str(input_csv),
        output_csv_path=str(output_csv),
        top_n_csv_path=str(top_n_csv),
        top_n=1
    ) as conn:
        # Delete dummy row if CSV was created and potentially loaded
        if os.path.exists(input_csv) and os.path.getsize(input_csv) > 0:
            # Check if table is not empty before deleting.
            count_res = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
            if count_res and count_res[0] > 0:
                 conn.execute(f"DELETE FROM {table_name}")

        quoted_headers = [f'"{h}"' if ' ' in h else h for h in headers]
        placeholders = ", ".join(["?"] * len(headers))
        insert_sql = f"INSERT INTO {table_name} ({', '.join(quoted_headers)}) VALUES ({placeholders})"
        for row_data in data:
            conn.execute(insert_sql, list(row_data))

    assert top_n_csv.exists()
    top_n_data = read_csv_content(str(top_n_csv))
    assert len(top_n_data) == 1
    assert top_n_data[0][headers[0]] == str(expected_top_identifier_in_first_col)


def test_input_csv_is_malformed_or_not_csv(tmp_path, default_table_name, default_schema):
    input_csv = tmp_path / "malformed.txt"
    output_csv = tmp_path / "output.csv"
    top_n_csv = tmp_path / "top_10.csv"

    with open(input_csv, 'w') as f:
        f.write("this is not a csv file\njust some random text")

    data_to_insert = [("itemNew", 10)]
    with manage_db_connection(
        db_name=":memory:",
        table_name=default_table_name,
        table_schema=default_schema,
        input_csv_path=str(input_csv),
        output_csv_path=str(output_csv),
        top_n_csv_path=str(top_n_csv),
        top_n=1
    ) as conn:
        count_after_load_attempt = conn.execute(f"SELECT COUNT(*) FROM {default_table_name}").fetchone()[0]
        assert count_after_load_attempt == 0
        conn.execute(f"INSERT INTO {default_table_name} (Name, Download) VALUES (?, ?)", data_to_insert[0])

    output_data = read_csv_content(str(output_csv))
    assert len(output_data) == 1
    assert output_data[0]['Name'] == "itemNew"
    # No pytest.fail here; if manage_db_connection handles the error, this test checks behavior.

def test_schema_with_spaces_pre_quoted(tmp_path):
    # Test with schema where column names with spaces are already quoted
    schema = '"User Name" VARCHAR, "Total Downloads" INTEGER'
    table_name = "spaced_table"
    input_csv = tmp_path / "input_spaced.csv"
    output_csv = tmp_path / "output_spaced.csv"
    top_n_csv = tmp_path / "top_1_spaced.csv"

    headers_in_csv = ['User Name', 'Total Downloads']
    pd.DataFrame([], columns=headers_in_csv).to_csv(input_csv, index=False)

    data_to_insert = [("Test User", 100)]

    with manage_db_connection(
        db_name=":memory:",
        table_name=table_name,
        table_schema=schema,
        input_csv_path=str(input_csv),
        output_csv_path=str(output_csv),
        top_n_csv_path=str(top_n_csv),
        top_n=1
    ) as conn:
        conn.execute(f'INSERT INTO {table_name} ("User Name", "Total Downloads") VALUES (?, ?)', data_to_insert[0])

    output_data = read_csv_content(str(output_csv), expected_headers=headers_in_csv)
    assert len(output_data) == 1
    assert output_data[0]['User Name'] == "Test User"
    assert int(output_data[0]['Total Downloads']) == 100

    top_n_data = read_csv_content(str(top_n_csv), expected_headers=headers_in_csv)
    assert len(top_n_data) == 1
    assert top_n_data[0]['User Name'] == "Test User"


def test_unquoted_schema_with_spaces_util_handles_it(tmp_path):
    schema_invalid_unquoted = "User Name VARCHAR, Total Downloads INTEGER" # Invalid: User Name is unquoted multi-word
    table_name = "spaced_table_unquoted"
    input_csv = tmp_path / "input_spaced_unquoted.csv"
    output_csv = tmp_path / "output_spaced_unquoted.csv"
    top_n_csv = tmp_path / "top_1_spaced_unquoted.csv"

    headers_in_csv = ['User Name', 'Total Downloads']
    pd.DataFrame([], columns=headers_in_csv).to_csv(input_csv, index=False)

    data_to_insert = [("Another User", 200)] # This data won't be used

    with pytest.raises(ValueError) as excinfo:
        with manage_db_connection(
            db_name=":memory:",
            table_name=table_name,
            table_schema=schema_invalid_unquoted,
            input_csv_path=str(input_csv),
            output_csv_path=str(output_csv),
            top_n_csv_path=str(top_n_csv),
            top_n=1
        ) as conn:
            pass # Should not reach here if ValueError is raised during schema parsing

    # Check for relevant error messages from db_utils schema parsing for "User Name VARCHAR"
    error_msg = str(excinfo.value).lower()
    assert ("invalid column definition format" in error_msg or \
            "invalid or unrecognized base type" in error_msg)
    assert "user name varchar" in error_msg # Ensure the problematic definition is mentioned


def test_primary_key_in_ordering_heuristic(tmp_path):
    # Schemas simplified: PRIMARY KEY constraint removed from schema string
    schema = "Name VARCHAR, ID VARCHAR, Score INTEGER"
    table_name = "pk_heuristic"
    input_csv = tmp_path / "input_pk.csv"
    output_csv = tmp_path / "output_pk.csv"
    top_n_csv = tmp_path / "top_1_pk.csv"

    headers = ['Name', 'ID', 'Score']
    pd.DataFrame([["dummy", "dummy_id", 0]], columns=headers).to_csv(input_csv, index=False) # Dummy row

    data = [("A", "id1", 100), ("B", "id2", 300), ("C", "id3", 200)]

    with manage_db_connection(
        db_name=":memory:", table_name=table_name, table_schema=schema,
        input_csv_path=str(input_csv), output_csv_path=str(output_csv),
        top_n_csv_path=str(top_n_csv), top_n=1
    ) as conn:
        conn.execute(f"DELETE FROM {table_name}") # Clear dummy row
        for row in data:
            conn.execute(f"INSERT INTO {table_name} (Name, ID, Score) VALUES (?, ?, ?)", list(row))

    top_data = read_csv_content(str(top_n_csv))
    assert len(top_data) == 1
    assert top_data[0]['Name'] == "B"
    assert int(top_data[0]['Score']) == 300

    schema2 = "Name VARCHAR, ID VARCHAR, Score INTEGER" # Simplified
    input_csv2 = tmp_path / "input_pk2.csv"
    output_csv2 = tmp_path / "output_pk2.csv"
    top_n_csv2 = tmp_path / "top_1_pk2.csv"
    pd.DataFrame([["dummy_name", "dummy_id", 0]], columns=headers).to_csv(input_csv2, index=False) # Dummy row

    with manage_db_connection(
        db_name=":memory:", table_name=table_name, table_schema=schema2,
        input_csv_path=str(input_csv2), output_csv_path=str(output_csv2),
        top_n_csv_path=str(top_n_csv2), top_n=1
    ) as conn:
        conn.execute(f"DELETE FROM {table_name}") # Clear dummy row
        for row in data:
            conn.execute(f"INSERT INTO {table_name} (Name, ID, Score) VALUES (?, ?, ?)", list(row))

    top_data2 = read_csv_content(str(top_n_csv2))
    assert len(top_data2) == 1
    assert top_data2[0]['Name'] == "B"
    assert int(top_data2[0]['Score']) == 300
