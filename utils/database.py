import ExcelImportProcessor


def bulk_to_sql_df(df, columns, model_cls):
    """ Inserting 3000 takes 774ms avg """
    engine = ExcelImportProcessor._get_sqlalchemy_engine()
    df[columns].to_sql(model_cls._meta.db_table, con=engine, if_exists='append', index=False)

def bulk_via_csv_df(df, columns, model_cls):
    """ Inserting 3000 takes 118ms avg """
    engine = ExcelImportProcessor._get_sqlalchemy_engine()
    connection = engine.raw_connection()
    output = StringIO()
    df[columns].to_csv(output, sep='\t', header=False, index=False)
    output.seek(0)
    contents = output.getvalue()
    cursor = connection.cursor()
    cursor.copy_from(output, model_cls._meta.db_table, null="", columns=columns)
    connection.commit()
    cursor.close()

def bulk_via_csv(file_path, columns, model_cls):
    """ Inserting 3000 takes 118ms avg """
    engine = ExcelImportProcessor._get_sqlalchemy_engine()
    connection = engine.raw_connection()
    with open(file_path, 'rb') as output:
        output.seek()
        cursor = connection.cursor()
        cursor.copy_from(output, model_cls._meta.db_table, null="", columns=columns)
        connection.commit()
        cursor.close()
