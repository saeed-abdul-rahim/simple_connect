# Simplify Connection to your Database

Simple Connect allows you to securely access your database and it supports SSH Connection
Currently it only supports SQL Databses.

### Sample Usage
```
from simple_connect import connect

conn = connect.Connect('sample_credential.json', 'database_name')

sample_table = conn.query('SELECT * FROM sample_table')
```

## Installation
```
pip install simple-connect
```

## Secure your Database credentials

Simple Connect tries to find your database / ssh credentials from a json file in ".credentials" folder which is in your home directory.
Example for windows, mac and linux respectively:
```
C:\Users\John\.credentials\sample.json

/Users/John/.credentials/sample.json

/home/John/.credentials/sample.json
```
Create the directory and the json file.

Json file should be in your following format:
```
{
  "SQL_HOST": "host_example<127.0.0.1>",
  "SQL_USER": "<username_of_your_sql>",
  "SQL_PASSWORD": "<password_of_your_sql>"
}
```

For SSH, you'll need to add additional keys:
```
{
  "SSH_USERNAME": "<ssh_username>",
  "SSH_PASSWORD": "<ssh_password>",
  "BASTION_HOST": "<sshBastion_host>"
  "SQL_HOST": "host_example<127.0.0.1>",
  "SQL_USER": "<username_of_your_sql>",
  "SQL_PASSWORD": "<password_of_your_sql>"
}
```

# Usage

Import
```
from simple_connect import connect
```

Basic connection:
```
conn = connect.Connect('sample_credential.json', 'database_name')
```

SSH connection:
```
conn = connect.BastionConnect('sample_credential.json', 'database_name')
```

## Querying

### Read
Query table (returns pandas dataframe):
```
sample_table = conn.query('SELECT * FROM sample_table')
```

### For Insert, Update and Delete -> Give dataframe rows that are required to update in table.

### Insert
Insert new table or append to existing table:
```
conn.to_db(dataframe, '<table_name>')
```

### Update
```
conn.update_table(dataframe, 'table_name', ['column_to_set1', 'column_to_set2', ...], ['columns_where_contition_applies', ...])
```
Example:
```
SQL:
UPDATE sample_table SET student = 'john', class = 5 WHERE id = 432 AND id_2 = 'SC'
UPDATE sample_table SET student = 'alisha', class = 5 WHERE id = 525 AND id_2 = 'SC'

Python:
conn.update_table(dataframe, 'sample_table', ['student', 'class'], ['id', 'id_2'])
```

### Delete
```
conn.delete_row(dataframe, 'table_name', ['columns_where_contition_applies', ...])
```
Example:
```
conn.delete_row(dataframe, 'sample_table', ['id', 'id_2'])
```
