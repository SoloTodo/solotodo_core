-- noinspection SqlNoDataSourceInspectionForFile

BEGIN;
--
-- Create model RSCategory
--
CREATE TABLE "category" (
	"id" integer NOT NULL PRIMARY KEY sortkey,
	"name" varchar(255) NOT NULL
) diststyle all;
--
-- Create model RSCountry
--
CREATE TABLE "country" (
	"id" integer NOT NULL PRIMARY KEY sortkey,
	"name" varchar(255) NOT NULL
) diststyle all;
--
-- Create model RSCurrency
--
CREATE TABLE "currency" (
	"id" integer NOT NULL PRIMARY KEY sortkey,
	"name" varchar(255) NOT NULL,
	"iso_code" varchar(10) NOT NULL,
	"exchange_rate" numeric(8, 2) NOT NULL,
	"exchange_rate_last_updated" timestamp with time zone NOT NULL
) diststyle all;
--
-- Create model RSProduct
--
CREATE TABLE "product" (
	"id" integer NOT NULL PRIMARY KEY sortkey,
	"name" varchar(255) NOT NULL,
	"creation_date" timestamp with time zone NOT NULL,
	"last_updated" timestamp with time zone NOT NULL,
	"category_id" integer NOT NULL,
	FOREIGN KEY ("category_id") REFERENCES "category" ("id")
) diststyle all;
--
-- Create model RSStoreType
--
CREATE TABLE "store_type" (
	"id" integer NOT NULL PRIMARY KEY sortkey,
	"name" varchar(255) NOT NULL
) diststyle all;
--
-- Create model RSStore
--
CREATE TABLE "store" (
	"id" integer NOT NULL PRIMARY KEY sortkey,
	"name" varchar(255) NOT NULL,
	"country_id" integer NOT NULL,
	"type_id" integer NOT NULL,
	FOREIGN KEY ("country_id") REFERENCES "country" ("id"),
	FOREIGN KEY ("type_id") REFERENCES "store_type" ("id")
) diststyle all;
--
-- Create model RSEntity
--
CREATE TABLE "entity" (
	"id" integer NOT NULL PRIMARY KEY sortkey distkey,
	"name" varchar(300) NOT NULL,
	"condition" varchar(100) NOT NULL,
	"part_number" varchar(50) NULL,
	"sku" varchar(50) NULL,
	"ean" varchar(15) NULL,
	"key" varchar(256) NOT NULL,
	"url" varchar(512) NOT NULL,
	"creation_date" timestamp with time zone NOT NULL,
	"last_updated" timestamp with time zone NOT NULL,
	"active_registry_id" integer NULL UNIQUE,
	"category_id" integer NOT NULL,
	"cell_plan_id" integer NULL,
	"currency_id" integer NOT NULL,
	"product_id" integer NOT NULL,
	"store_id" integer NOT NULL,
	"estimated_sales" integer NOT NULL,
	"is_available" boolean NOT NULL,
	FOREIGN KEY ("category_id") REFERENCES "category" ("id"),
	FOREIGN KEY ("cell_plan_id") REFERENCES "product" ("id"),
	FOREIGN KEY ("currency_id") REFERENCES "currency" ("id"),
	FOREIGN KEY ("product_id") REFERENCES "product" ("id"),
	FOREIGN KEY ("store_id") REFERENCES "store" ("id")
);
--
-- Create model RSEntityHistory
--
CREATE TABLE "entity_history" (
	"id" integer NOT NULL PRIMARY KEY,
	"timestamp" timestamp with time zone NOT NULL sortkey,
	"stock" integer NOT NULL,
	"normal_price" numeric(12, 2) NOT NULL,
	"offer_price" numeric(12, 2) NOT NULL,
	"cell_monthly_payment" numeric(12, 2) NULL,
	"entity_id" integer NOT NULL distkey,
	FOREIGN KEY ("entity_id") REFERENCES "entity" ("id")
);


ALTER TABLE "entity" ADD CONSTRAINT "entity_active_registry_id_ded8b095_fk_entity_history_id" FOREIGN KEY ("active_registry_id") REFERENCES "entity_history" ("id") DEFERRABLE INITIALLY DEFERRED;

COMMIT;
