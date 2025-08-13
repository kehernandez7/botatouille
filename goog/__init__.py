from google.cloud import storage

storage_client = storage.Client()
bucket_name = "botatouille-art"
bucket = storage_client.get_bucket(bucket_name)
