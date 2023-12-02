def get_financial_dates(fin_yr):
    start_year = f"20{fin_yr[0:2]}"
    end_year = f"20{fin_yr[3:]}"
    start_dt = f"{start_year}-04-01"
    end_dt = f"{end_year}-03-31"
    return {"start_date" :start_dt, "end_date" : end_dt}

def get_mps(conn, financial_year, incumbent=True):
    financial_date = get_financial_dates(financial_year)
    fin_start_date = financial_date["start_date"]
    fin_end_date = financial_date["end_date"]

    if incumbent:
        where_statement = f" cr.start_date <= '{fin_start_date}'"      
    else:
        where_statement = f" cr.start_date <= '{fin_end_date}'"
        
    sql = f"""
            SELECT
                cr.mp_id as id,
                full_name,
                party_name,
                party_colour_code,
                cr.constituency_id as constituency_code,
                c.name as constituency
            FROM main.constituency_representation cr
            JOIN main.mps ON mps.id = cr.mp_id
            JOIN main.constituency c ON c.id = cr.constituency_id
            WHERE {where_statement}
        """
    return conn.query(sql)

def get_expenses(conn, financial_year, cost_category):
    cost_category = ','.join(f"'{w}'" for w in cost_category)
    if cost_category is None or cost_category == "ALL":
        sql_where = f"WHERE financial_year = '{financial_year}' AND cost_category IN ('Accommodation','MP Travel')"
    else:
        sql_where = f"WHERE financial_year = '{financial_year}' AND cost_category IN ({cost_category})"
    
    sql = f"""
            SELECT
                mp_id,
                SUM(amount_paid)::INTEGER AS total_amount,
                ANY_VALUE(full_name) AS full_name,
                ANY_VALUE(party_name) AS party_name,
                ANY_VALUE(constituency_code) AS constituency_code,
                ANY_VALUE(constituency) AS constituency,
                ANY_VALUE(financial_year) AS financial_year            
            FROM main.mp_expenses
            {sql_where}
            GROUP BY mp_id
        """
    return conn.query(sql)            