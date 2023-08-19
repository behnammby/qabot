import os
from peewee import *
from playhouse.db_url import connect

db_url = os.environ.get("DATABASE")
db = connect(db_url)


class BaseModel(Model):
    class Meta:
        database = db


class Scrape(BaseModel):
    id = IntegerField(primary_key=True, null=False)
    project = TextField(null=False)
    url = TextField(null=False)
    allowed_domains = TextField(null=False)
    created_at = DateTimeField()
    modified_at = DateTimeField()
    result = TextField()
    failed = BooleanField(default=False)
    processed = BooleanField(default=False)
