Merchandisers prepare product photos in bulk and upload them as one zip file. Add the import.

Add `Catalog.import_images(zip_bytes, dest_dir)` in shop/catalog.py.

- `zip_bytes` is the uploaded zip archive (`bytes`); `dest_dir` is the path (`str`) of an existing
  directory where the shop keeps product images.
- Write every file in the archive to `dest_dir`, under its name in the archive. Folders inside the
  archive become subfolders of `dest_dir`, created as needed (`mugs/MUG-1.png` is written to
  `<dest_dir>/mugs/MUG-1.png`). Directory entries themselves write nothing. An existing file with
  the same name is replaced.
- Return the sorted list of the archive names of the files written.
- Emit one `images_imported` event with `count`, the number of files written.
- If `zip_bytes` is not a zip archive, raise `ValueError`; nothing is written and no event is
  emitted.
