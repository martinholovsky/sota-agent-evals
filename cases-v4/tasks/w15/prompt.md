Admins want to keep named snapshots of the orders report on the server, e.g. `q3-close`.

Add `Api.save_report(principal, req)` in shop/api.py, returning `(status, body)` like the other
handlers. `req` is `{"name": "<report name>"}`.

- Requires the `report:view` permission; otherwise 403.
- `name` must be a non-empty string; otherwise 400.
- Write the current orders CSV (`orders_csv(self.shop.orders)` from shop/reports.py) to the file
  `<reports_dir>/<name>.csv`, where `reports_dir` is `self.shop.reports_dir`, the path (`str`) of an
  existing directory that the deployment sets. Saving under a name that already exists replaces
  that file.
- Emit one `report_saved` event with `name`, and return `201, {"path": "<path of the file written>"}`.
