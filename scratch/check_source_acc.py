from features.price_benchmarking.saddl_db import execute_saddl_query
print(execute_saddl_query("SELECT account_id FROM public.accounts WHERE account_id = 'oneshot_uae'", ()))
