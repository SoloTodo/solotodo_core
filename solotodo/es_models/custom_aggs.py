from elasticsearch_dsl.aggs import Bucket


class Parent(Bucket):
    name = 'parent'
