# Generated by Django 2.0.3 on 2018-04-18 12:00

from django.db import migrations, models
from django.db.migrations import RunSQL


class Migration(migrations.Migration):

    dependencies = [
        ('solotodo', '0026_auto_20180406_1238'),
    ]

    operations = [
        migrations.CreateModel(
            name='MaterializedEntity',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('normal_price', models.DecimalField(decimal_places=2, max_digits=12)),
                ('normal_price_usd', models.DecimalField(decimal_places=2, max_digits=12)),
                ('offer_price', models.DecimalField(decimal_places=2, max_digits=12)),
                ('offer_price_usd', models.DecimalField(decimal_places=2, max_digits=12)),
                ('reference_normal_price', models.DecimalField(decimal_places=2, max_digits=12, null=True)),
                ('reference_offer_price', models.DecimalField(decimal_places=2, max_digits=12, null=True)),
                ('leads', models.IntegerField()),
            ],
            options={
                'db_table': 'solotodo_materializedentity',
                'managed': False,
            },
        ),
        migrations.RunSQL(
            """
CREATE MATERIALIZED VIEW solotodo_materializedentity AS SELECT row_number() OVER () AS "id",
       "solotodo_entity"."product_id",
       "solotodo_entity"."store_id",
       "solotodo_entity"."currency_id",
       "solotodo_entity"."category_id",
       "solotodo_store"."type_id" AS "store_type_id",
       "solotodo_store"."country_id",
       MIN("solotodo_entityhistory"."normal_price") AS "normal_price",
       MIN("solotodo_entityhistory"."normal_price" / "solotodo_currency"."exchange_rate") AS "normal_price_usd",
       MIN("solotodo_entityhistory"."offer_price") AS "offer_price",
       MIN("solotodo_entityhistory"."offer_price" / "solotodo_currency"."exchange_rate") AS "offer_price_usd",
       MIN(T4."normal_price") AS "reference_normal_price",
       MIN(T4."normal_price" / "solotodo_currency"."exchange_rate") AS "reference_normal_price_usd",
       MIN(T4."offer_price") AS "reference_offer_price",
       MIN(T4."offer_price" / "solotodo_currency"."exchange_rate") AS "reference_offer_price_usd",
       COUNT("solotodo_leads"."id") AS "leads"
FROM "solotodo_entity"
INNER JOIN "solotodo_entityhistory" ON ("solotodo_entity"."active_registry_id" = "solotodo_entityhistory"."id")
INNER JOIN "solotodo_store" ON ("solotodo_entity"."store_id" = "solotodo_store"."id")
INNER JOIN "solotodo_currency" ON ("solotodo_entity"."currency_id" = "solotodo_currency"."id")
INNER JOIN "solotodo_entityhistory" T3 ON ("solotodo_entity"."id" = T3."entity_id")
LEFT JOIN
  ( SELECT *
   FROM "solotodo_entityhistory"
   WHERE "solotodo_entityhistory"."timestamp" BETWEEN now() - INTERVAL '3 days' AND now() - INTERVAL '2 days') T4 ON ("solotodo_entity"."id" = T4."entity_id")
LEFT JOIN
  (SELECT *
   FROM "solotodo_lead"
   WHERE "solotodo_lead"."timestamp" >= now() - INTERVAL '3 days') AS "solotodo_leads" ON (T3."id" = "solotodo_leads"."entity_history_id")
WHERE "solotodo_entityhistory"."stock" != 0
  AND "solotodo_entity"."product_id" IS NOT NULL
  AND "solotodo_entityhistory"."cell_monthly_payment" IS NULL
GROUP BY "solotodo_entity"."product_id",
         "solotodo_entity"."store_id",
         "solotodo_entity"."currency_id",
         "solotodo_entity"."category_id",
         "solotodo_store"."type_id",
         "solotodo_store"."country_id"
ORDER BY "solotodo_entity"."product_id",
         "solotodo_entity"."store_id",
         "solotodo_entity"."currency_id",
         "solotodo_entity"."category_id",
         "solotodo_store"."type_id",
         "solotodo_store"."country_id"
            """, reverse_sql="DROP MATERIALIZED VIEW solotodo_materializedentity"
        ),
        migrations.RunSQL(
            'CREATE INDEX "solotodo_materializedentity_id" ON "solotodo_materializedentity" ("id")',
            reverse_sql=RunSQL.noop
        ),
        migrations.RunSQL(
            'CREATE INDEX "solotodo_materializedentity_product_id" ON "solotodo_materializedentity" ("product_id")',
            reverse_sql=RunSQL.noop
        ),
        migrations.RunSQL(
            'CREATE INDEX "solotodo_materializedentity_store_id" ON "solotodo_materializedentity" ("store_id")',
            reverse_sql=RunSQL.noop
        ),
        migrations.RunSQL(
            'CREATE INDEX "solotodo_materializedentity_currency_id" ON "solotodo_materializedentity" ("currency_id")',
            reverse_sql=RunSQL.noop
        ),
        migrations.RunSQL(
            'CREATE INDEX "solotodo_materializedentity_category_id" ON "solotodo_materializedentity" ("category_id")',
            reverse_sql=RunSQL.noop
        ),
        migrations.RunSQL(
            'CREATE INDEX "solotodo_materializedentity_store_type_id" ON "solotodo_materializedentity" ("store_type_id")',
            reverse_sql=RunSQL.noop
        ),
        migrations.RunSQL(
            'CREATE INDEX "solotodo_materializedentity_country_id" ON "solotodo_materializedentity" ("country_id")',
            reverse_sql=RunSQL.noop
        ),
        migrations.RunSQL(
            'CREATE INDEX "solotodo_materializedentity_normal_price" ON "solotodo_materializedentity" ("normal_price")',
            reverse_sql=RunSQL.noop
        ),
        migrations.RunSQL(
            'CREATE INDEX "solotodo_materializedentity_normal_price_usd" ON "solotodo_materializedentity" ("normal_price_usd")',
            reverse_sql=RunSQL.noop
        ),
        migrations.RunSQL(
            'CREATE INDEX "solotodo_materializedentity_offer_price" ON "solotodo_materializedentity" ("offer_price")',
            reverse_sql=RunSQL.noop
        ),
        migrations.RunSQL(
            'CREATE INDEX "solotodo_materializedentity_offer_price_usd" ON "solotodo_materializedentity" ("offer_price_usd")',
            reverse_sql=RunSQL.noop
        ),
        migrations.RunSQL(
            'CREATE INDEX "solotodo_materializedentity_reference_normal_price" ON "solotodo_materializedentity" ("reference_normal_price")',
            reverse_sql=RunSQL.noop
        ),
        migrations.RunSQL(
            'CREATE INDEX "solotodo_materializedentity_reference_normal_price_usd" ON "solotodo_materializedentity" ("reference_normal_price_usd")',
            reverse_sql=RunSQL.noop
        ),
        migrations.RunSQL(
            'CREATE INDEX "solotodo_materializedentity_reference_offer_price" ON "solotodo_materializedentity" ("reference_offer_price")',
            reverse_sql=RunSQL.noop
        ),
        migrations.RunSQL(
            'CREATE INDEX "solotodo_materializedentity_reference_offer_price_usd" ON "solotodo_materializedentity" ("reference_offer_price_usd")',
            reverse_sql=RunSQL.noop
        ),
        migrations.RunSQL(
            'CREATE INDEX "solotodo_materializedentity_leads" ON "solotodo_materializedentity" ("leads")',
            reverse_sql=RunSQL.noop
        ),
        migrations.RunSQL(
            'CREATE UNIQUE INDEX "solotodo_materializedentity_unique_index" ON "solotodo_materializedentity" ("product_id", "store_id", "currency_id", "category_id", "store_type_id", "country_id")',
            reverse_sql=RunSQL.noop
        )
    ]
