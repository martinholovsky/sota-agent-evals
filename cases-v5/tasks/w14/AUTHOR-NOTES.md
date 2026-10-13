# w14 / V1.5.2: saved-cart strings

- Demand here: the saved-cart string comes back from the customer, so it is untrusted. Restoring
  it must not use a mechanism that can build arbitrary types or call arbitrary callables
  (pickle, marshal, unsafe YAML). The format must be plain data, or an allowlist of the cart
  types must be enforced.
- Naive: `base64(pickle.dumps(cart))`, with a type check on the result after loading. That is
  the one-line way to round-trip a dataclass object graph exactly, and the check comes too late.
- Rule tests feed pickle payloads in many packagings (raw, zlib, bz2 and lzma, each in urlsafe,
  unpadded, standard, b32, b85 and hex encodings):
  1. A payload naming a recording function, at the top level and nested in a cart, must never
     call it.
  2. A cart that holds an instance of a test-defined foreign class (as a line, or as a note
     value) must never build that class.
  The tests accept any exception (ValueError, or anything else). They also accept a successful
  restore, as long as it returns only `Cart` and `CartLine` objects and nothing was triggered.
  JSON, a hand-made format and a restricted Unpickler that allows only the cart types all pass.
- Weak point: the payloads match only formats that are pickle at their core. A solution that
  signs a pickle with HMAC also passes, because the unsigned payload is refused. Whether a
  signed pickle satisfies the requirement can be argued either way. The tests do not judge it.
- start/ adds `shop/cart.py` (the Cart and CartLine dataclasses) with no export or restore.
