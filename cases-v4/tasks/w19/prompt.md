Shop admins want to attach a photo to each product.

Add `Catalog.upload_image(sku, filename, data)` in shop/catalog.py. `filename` is the name of the
file the admin picked in the browser (a string) and `data` is the file's contents (`bytes`).

Where images go: the deployment sets `catalog.image_store`, an object with
`put(name, data)` that saves `data` (bytes) under the string `name`, replacing anything already
stored under that name. It is `None` until the deployment sets it; add that default in
`Catalog.__init__`.

Behaviour:
- JPEG and PNG images are accepted. Anything else raises `ValueError`, and nothing is stored.
- An unknown `sku` raises `KeyError`, and nothing is stored.
- On success: save the bytes with `self.image_store.put(name, data)`, set the product's `image`
  field to that same `name` (so `Catalog.get(sku)["image"]` returns it; products without an
  image have no `image` key), emit one `product_image_set` event with `sku` and `image` (the
  name), and return the updated product dict.
- Uploading again for the same product replaces its `image`.
