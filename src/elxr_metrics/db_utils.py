import duckdb
import os
import pandas as pd
from contextlib import contextmanager
import re

# Define known base SQL types. The first word of a type definition must be one of these.
KNOWN_BASE_SQL_TYPES = {
    "VARCHAR", "INTEGER", "TEXT", "REAL", "FLOAT", "DOUBLE", "DECIMAL",
    "BLOB", "DATE", "TIMESTAMP", "BOOLEAN", "UUID", "INTERVAL",
    "ARRAY", "STRUCT", "MAP", "UNION", "ANY", "VARIANT"
}

@contextmanager
def manage_db_connection(db_name: str, table_name: str, table_schema: str, input_csv_path: str, output_csv_path: str, top_n_csv_path: str, top_n: int = 10):
    """
    Manages a DuckDB database connection, table creation, data loading, and saving.

    Schema Definition Rules:
    - Column definitions are separated by commas (commas in type parameters like DECIMAL(N,M) are respected).
    - Each definition MUST be in the format: 'Name Type' or '"Quoted Name" Type'.
    - 'Name': If unquoted, must be a single valid SQL identifier (alphanumeric + underscore). No spaces.
    - '"Quoted Name"': If name contains spaces or special characters, it MUST be enclosed in double quotes.
    - 'Type': The type definition (e.g., VARCHAR, INTEGER PRIMARY KEY, DECIMAL(10,2)). The first word
              of the type definition must be a known base SQL type.

    Args:
        db_name (str): The name of the database.
        table_name (str): The name of the table to create.
        table_schema (str): Schema string, e.g., 'ID INTEGER PRIMARY KEY, Name VARCHAR, Value FLOAT'.
        input_csv_path (str): Path to the input CSV. Loaded if exists and not empty.
        output_csv_path (str): Path to save the full table data.
        top_n_csv_path (str): Path to save the top N rows.
        top_n (int): Number of top rows to save.
    Raises:
        ValueError: If `table_schema` is invalid.
    """
    con = None
    try:
        con = duckdb.connect(database=db_name, read_only=False)

        cols_processed = []
        # Split schema by comma, but not commas inside parentheses
        col_defs_list = re.split(r',(?![^\(]*\))', table_schema)

        for col_def_str in col_defs_list:
            col_def_str = col_def_str.strip()
            if not col_def_str: continue

            name_part_final = ""
            type_part_final = ""

            # Regex: Group 1 for quoted name content, Group 2 for unquoted single-word name, Group 3 for the rest (type and constraints).
            match = re.match(r'^\s*(?:"([^"]+)"|([a-zA-Z0-9_]+))\s+(.+)\s*$', col_def_str)

            if match:
                if match.group(1): # Quoted name: "User Name"
                    name_part_final = f'"{match.group(1)}"'
                else: # Unquoted name: Name
                    name_part_final = match.group(2) # This is a single word

                type_part_final = match.group(3).strip()

                if not type_part_final:
                    raise ValueError(f"Type information is missing for column '{name_part_final}' in definition: '{col_def_str}'")

                # Validate the beginning of type_part_final
                base_type_candidate = type_part_final.split(" ", 1)[0].split("(",1)[0].upper()
                if base_type_candidate not in KNOWN_BASE_SQL_TYPES:
                    raise ValueError(f"Invalid or unrecognized base type '{base_type_candidate}' for column '{name_part_final}' in definition: '{col_def_str}'. If column name has spaces and was intended as part of name, please quote it (e.g., '\"{name_part_final} {base_type_candidate}\" ...').")
            else:
                raise ValueError(f"Invalid column definition format: '{col_def_str}'. Expected 'Name Type' or '\"Quoted Name\" Type'. Unquoted names must be single words, and type information is mandatory.")

            cols_processed.append(f'{name_part_final} {type_part_final}')

        if not cols_processed:
            raise ValueError("Table schema resulted in no columns to process. Schema string might be empty or malformed.")

        safe_table_schema_for_create = ', '.join(cols_processed)
        con.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({safe_table_schema_for_create})")

        if os.path.exists(input_csv_path) and os.path.getsize(input_csv_path) > 0:
            try:
                con.execute(f"COPY {table_name} FROM '{input_csv_path}' (HEADER)")
            except duckdb.Error as e:
                print(f"Warning: Could not load data from CSV '{input_csv_path}'. Error: {e}")

        yield con

        con.execute(f"COPY {table_name} TO '{output_csv_path}' (HEADER, DELIMITER ',')")

        result = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
        if result and result[0] > 0:
            try:
                columns_desc = con.execute(f"DESCRIBE {table_name}").fetchall()
                order_by_column_for_top_n = ""
                if columns_desc:
                    order_by_column_for_top_n = columns_desc[0][0]

                potential_order_columns = [col[0] for col in columns_desc if col[1].upper() in ('INTEGER', 'BIGINT', 'FLOAT', 'DOUBLE', 'DECIMAL', 'NUMERIC')]

                if potential_order_columns:
                    order_by_column_for_top_n = potential_order_columns[0]
                    preferred_names = ['DOWNLOAD', 'DOWNLOADS', 'COUNT', 'VALUE', 'SCORE', 'RATING']
                    for col_name_pref in preferred_names:
                        for poc_tuple in columns_desc:
                            poc_name = poc_tuple[0]
                            if poc_name.upper() == col_name_pref and poc_name in potential_order_columns:
                                order_by_column_for_top_n = poc_name
                                break
                        if order_by_column_for_top_n.upper() == col_name_pref:
                            break
                elif not columns_desc :
                     raise ValueError("Cannot describe table columns to determine ordering key.")

                if not order_by_column_for_top_n:
                     raise ValueError("Could not determine a column to order by for top N (no suitable column found or DESCRIBE failed).")

                if ' ' in order_by_column_for_top_n and not (order_by_column_for_top_n.startswith('"') and order_by_column_for_top_n.endswith('"')):
                    order_by_column_for_top_n_quoted = f'"{order_by_column_for_top_n}"'
                else:
                    order_by_column_for_top_n_quoted = order_by_column_for_top_n

                con.execute(f"COPY (SELECT * FROM {table_name} ORDER BY {order_by_column_for_top_n_quoted} DESC LIMIT {top_n}) TO '{top_n_csv_path}' (HEADER, DELIMITER ',')")
            except duckdb.Error as e:
                print(f"Could not save top N rows (DuckDB error): {e}. Table: {table_name}")
            except ValueError as e:
                 print(f"Could not save top N rows (Configuration error): {e}. Table: {table_name}")
        else:
            pd.DataFrame().to_csv(top_n_csv_path, index=False)
    finally:
        if con:
            con.close()
