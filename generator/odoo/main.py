import argparse
import xmlrpc.client

from utils.sales import generate_sales
from utils.vendors import generate_vendors
from utils.purchase import generate_purchase
from utils.invoices import generate_invoices
from utils.inventory import generate_inventory
from utils.hr import generate_hr

URL = "http://localhost:8069"
DB = "odoo_dev_18"
USERNAME = "admin"
PASSWORD = "admin"


def connect():
    common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common")
    uid = common.authenticate(DB, USERNAME, PASSWORD, {})
    if not uid:
        raise Exception("Authentication failed")
    models = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object")
    return uid, models


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sales", action="store_true")
    parser.add_argument("--vendors", action="store_true")
    parser.add_argument("--purchase", action="store_true")
    parser.add_argument("--invoices", action="store_true")
    parser.add_argument("--inventory", action="store_true")
    parser.add_argument("--hr", action="store_true")
    args = parser.parse_args()

    run_all = not any([args.sales, args.vendors, args.purchase, args.invoices, args.inventory, args.hr])

    cfg = {"url": URL, "db": DB, "password": PASSWORD}
    uid, models = connect()
    print(f"Connected as uid={uid}")

    def search_ids(model, domain=None):
        return models.execute_kw(cfg["db"], uid, cfg["password"], model, "search", [domain or []])

    if args.sales or run_all:
        generate_sales(uid, models, cfg)

    if args.vendors or run_all:
        product_ids = search_ids("product.product", [["sale_ok", "=", True]])
        generate_vendors(uid, models, cfg, product_ids)

    if args.purchase or run_all:
        product_ids = search_ids("product.product", [["sale_ok", "=", True]])
        vendor_ids = search_ids("res.partner", [["supplier_rank", ">", 0]])
        generate_purchase(uid, models, cfg, vendor_ids, product_ids)

    if args.invoices or run_all:
        generate_invoices(uid, models, cfg)

    if args.inventory or run_all:
        product_ids = search_ids("product.product", [["sale_ok", "=", True]])
        generate_inventory(uid, models, cfg, product_ids)

    if args.hr or run_all:
        generate_hr(uid, models, cfg)


if __name__ == "__main__":
    main()
