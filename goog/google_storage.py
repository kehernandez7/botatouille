from goog import bucket


def upload_to_bucket(filename):
    blob = bucket.blob(filename)
    generation_match_precondition = 0
    blob.upload_from_filename(filename, if_generation_match=generation_match_precondition)

    print(
        'img uploaded'
    )


def download_from_bucket(filename):
    blob = bucket.blob(filename)
    blob.download_to_filename(filename)
