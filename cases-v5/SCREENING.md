# cases-v5 screening (blind screener, 2026-10-13)

Produced per SELECTION.md "Screening" by an agent whose 5 tool calls read only the ordered requirement texts (held outside this repo, licence) and a copy of `base/`; audited from its transcript: no tool input or result names SOTA-skills, an installed skill, or a cases-v1–v4 task. Own words only (7-word overlap with the ASVS text: 0).

# ASVS 5.0.0 screening for the shop case set

| rank | id | verdict | reason (own words; failing criterion for INELIGIBLE, task sketch for ELIGIBLE) |
|---|---|---|---|
| 1 | V5.2.6 | INELIGIBLE | E1: image upload and pixel decoding is not a kind of behaviour the shop has or could plausibly gain in one feature. |
| 2 | V15.4.1 | INELIGIBLE | E2: race conditions in threaded code cannot be shown deterministically by an in-process unittest without timing. |
| 3 | V6.7.1 | INELIGIBLE | E1: certificate storage for crypto assertions is infrastructure/key management. |
| 4 | V12.1.1 | INELIGIBLE | E1/E2: TLS protocol versions (transport). |
| 5 | V6.8.3 | INELIGIBLE | E1: SAML identity-provider protocol the shop does not use. |
| 6 | V10.3.3 | INELIGIBLE | E1: OAuth resource-server claim handling, a protocol outside the shop. |
| 7 | V4.1.3 | INELIGIBLE | E1: intermediary/proxy header handling is deployment infrastructure. |
| 8 | V14.2.2 | INELIGIBLE | E1: caching in load balancers and server components is infrastructure. |
| 9 | V3.4.7 | INELIGIBLE | E1: browser security header (CSP reporting). |
| 10 | V12.1.4 | INELIGIBLE | E1/E2: certificate revocation / OCSP stapling (TLS). |
| 11 | V3.3.3 | INELIGIBLE | E1: browser cookie naming. |
| 12 | V3.4.4 | INELIGIBLE | E1: browser response header. |
| 13 | V9.1.1 | ELIGIBLE | Task: add stateless signed login tokens that handlers can accept in place of a principal; test forges/tampers a token's payload (e.g. role) and checks it is refused before any of its contents are used. |
| 14 | V6.4.2 | INELIGIBLE | E4: no natural request leads a straightforward implementation to add hints or secret questions without the request asking for them; otherwise it is an absence-of-feature design check. |
| 15 | V1.3.9 | INELIGIBLE | E1: memcache is not part of the shop. |
| 16 | V15.1.1 | INELIGIBLE | E1/E2: documentation of remediation time frames. |
| 17 | V6.8.4 | INELIGIBLE | E1: IdP/OIDC authentication-strength claims. |
| 18 | V10.4.7 | INELIGIBLE | E1: OAuth authorization-server internals. |
| 19 | V10.4.6 | INELIGIBLE | E1: OAuth authorization-server internals (PKCE). |
| 20 | V13.2.5 | INELIGIBLE | E1: server-level configuration of outbound destinations (configuration, not application behaviour). |
| 21 | V14.2.6 | ELIGIBLE | Task: let customers save a payment method/card reference and view it in their account; test checks the view handler returns only a masked tail of the stored number, never the whole value. |
| 22 | V16.3.1 | ELIGIBLE | Task: add a second way to authenticate (e.g. staff PIN or integration API key); test drives a good and a bad attempt and checks an event is emitted for each, naming the method used. |
| 23 | V6.5.1 | ELIGIBLE | Task: add emailed one-time login codes (or printable backup codes); test logs in with a code, then replays the same code and expects it to be refused. |
| 24 | V12.3.2 | INELIGIBLE | E1/E2: TLS client certificate validation (transport). |
| 25 | V1.4.2 | INELIGIBLE | E1: integer overflow does not arise with Python's arbitrary-precision ints. |
| 26 | V6.2.2 | INELIGIBLE | E4: the requirement is that the feature exists; a request cannot be violated by its straightforward implementation without stating it. |
| 27 | V2.3.3 | INELIGIBLE | E3: README convention 6 (all-or-nothing operations) already states it. |
| 28 | V14.3.2 | INELIGIBLE | E1: browser anti-caching response headers. |
| 29 | V3.5.7 | INELIGIBLE | E1: browser script-inclusion (XSSI). |
| 30 | V12.3.3 | INELIGIBLE | E1/E2: internal transport encryption (TLS). |
| 31 | V5.2.3 | INELIGIBLE | E1: compressed-file upload handling is not a kind of behaviour the shop has or could plausibly gain in one feature. |
| 32 | V6.4.3 | INELIGIBLE | E1: needs both an MFA mechanism and a reset flow; more than one feature for this shop. |
| 33 | V10.3.4 | INELIGIBLE | E1: OAuth resource-server token claims. |
| 34 | V14.1.2 | INELIGIBLE | E1/E2: data-protection documentation. |
| 35 | V1.3.8 | INELIGIBLE | E1: JNDI is Java-specific and absent. |
| 36 | V4.2.1 | INELIGIBLE | E1/E2: HTTP message framing / request smuggling (infrastructure). |
| 37 | V17.2.5 | INELIGIBLE | E1: WebRTC media server. |
| 38 | V6.2.4 | INELIGIBLE | E2: compliance depends on which external common-password list the implementation embeds, which a deterministic test cannot pin fairly. |
| 39 | V1.3.7 | ELIGIBLE | Task: let customers attach a gift message that is merged into the order confirmation text template; test submits a message containing template/format placeholders (e.g. ones naming order fields) and checks they come out literally, not expanded. |
| 40 | V3.7.5 | INELIGIBLE | E1: browser feature detection. |
| 41 | V17.2.1 | INELIGIBLE | E1: WebRTC DTLS key management. |
| 42 | V15.3.1 | ELIGIBLE | Task: add an admin handler to look up a customer account (with its orders); test checks the response contains only the intended fields and never internal ones such as the password salt/hash. |
| 43 | V11.4.1 | INELIGIBLE | E1: cryptographic hash algorithm choice. |
| 44 | V12.3.5 | INELIGIBLE | E1: service-to-service mutual authentication / PKI. |
| 45 | V7.3.1 | ELIGIBLE | Task: add server-side session tokens issued at login and accepted by handlers; test advances the shop clock by a long idle period and checks the token is no longer accepted. |
| 46 | V12.1.2 | INELIGIBLE | E1: TLS cipher-suite configuration. |
| 47 | V13.4.3 | INELIGIBLE | E1: web-server directory listing configuration. |
| 48 | V16.2.1 | ELIGIBLE | Task: let admins issue partial refunds (or change prices through a handler); test checks the resulting event records who did it and on which object, in addition to the time. |
| 49 | V12.1.5 | INELIGIBLE | E1: TLS Encrypted Client Hello. |
| 50 | V1.2.10 | ELIGIBLE | Task: extend the CSV export with product names or a customer contact export; test creates a value starting with a spreadsheet formula character and checks the exported cell is neutralised with a leading quote. |
| 51 | V15.2.4 | INELIGIBLE | E1: dependency sourcing / supply chain. |
| 52 | V17.2.3 | INELIGIBLE | E1: WebRTC SRTP. |
| 53 | V9.2.3 | INELIGIBLE | E4: the shop is a single service, so a token audience mismatch only arises if the request itself introduces a second recipient service. |
| 54 | V6.5.8 | INELIGIBLE | E3: README convention 9 already says time comes from the shop clock. |
| 55 | V10.5.4 | INELIGIBLE | E1: OIDC client ID-token audience. |
| 56 | V7.3.2 | ELIGIBLE | Task: add sessions that are extended on each use (sliding expiry); test keeps a session active with frequent requests over a very long span of shop-clock time and checks it eventually stops being accepted. |
| 57 | V5.4.3 | INELIGIBLE | E1/E2: antivirus scanning of files. |
| 58 | V10.4.1 | INELIGIBLE | E1: OAuth redirect-URI validation. |
| 59 | V6.4.6 | ELIGIBLE | Task: let admins help a locked-out customer regain access; test checks the admin path cannot set a chosen password and the admin's response contains nothing that lets the admin log in as the customer. |
| 60 | V5.3.3 | INELIGIBLE | E1: archive decompression paths (file handling outside the shop). |
| 61 | V6.2.8 | ELIGIBLE | Task: make login tolerant of user typing (trim whitespace, case-insensitive usernames); test checks a password differing only by case or surrounding whitespace is still rejected. |
| 62 | V6.5.2 | ELIGIBLE | Task: add printable account-recovery codes; test inspects the user store after generation and checks the issued codes are not held in plaintext (and differ in storage between users with salting). |
| 63 | V1.5.2 | ELIGIBLE | Task: let customers export and later restore a saved cart as an opaque string; test feeds a crafted serialized payload that would run code or build arbitrary objects and checks it is refused without side effects. |
| 64 | V8.1.4 | INELIGIBLE | E1/E2: authorization documentation. |
| 65 | V5.4.1 | INELIGIBLE | E1: download filenames and response headers lie outside the handler (status, body) contract. |
| 66 | V16.2.2 | INELIGIBLE | E3: events already carry zone-free unix seconds from the shop clock (README 9 / events.py). |
| 67 | V15.2.3 | INELIGIBLE | E1: production deployment contents. |
| 68 | V7.1.3 | INELIGIBLE | E1/E2: federated session documentation. |
| 69 | V17.1.2 | INELIGIBLE | E1: WebRTC TURN server. |
| 70 | V8.3.2 | INELIGIBLE | E3/E4: README 4 already makes permission changes take effect at call time, and for user-level changes it tells handlers to trust the principal and not re-check the store, so a compliant fix would contradict a stated convention. |
| 71 | V9.2.2 | ELIGIBLE | Task: add signed tokens for both login sessions and password-reset links; test presents a reset token where a session token is expected (and vice versa) and checks it is refused. |
| 72 | V15.3.4 | INELIGIBLE | E1: proxy/middleware client-IP propagation is infrastructure. |
| 73 | V1.2.7 | INELIGIBLE | E1: XPath/XML data stores are not plausible for the shop in one feature. |
| 74 | V10.4.10 | INELIGIBLE | E1: OAuth back-channel client authentication. |
| 75 | V3.5.2 | INELIGIBLE | E1: browser CORS preflight. |
| 76 | V10.7.3 | INELIGIBLE | E1: OAuth consent management. |
| 77 | V10.5.2 | INELIGIBLE | E1: OIDC client subject identification. |
| 78 | V10.6.2 | INELIGIBLE | E1: OpenID Provider logout. |
| 79 | V7.2.1 | INELIGIBLE | E1: architectural placement of session verification; the shop has no client-side component. |
| 80 | V6.2.1 | INELIGIBLE | E3: base already enforces a 12-character minimum. |
| 81 | V6.4.4 | INELIGIBLE | E1/E2: identity proofing on factor loss is an organisational process. |
| 82 | V2.3.5 | INELIGIBLE | E4: what counts as high-value is undefined unless the request states a threshold, so a test would be unfair. |
| 83 | V4.2.2 | INELIGIBLE | E1: HTTP message framing. |
| 84 | V4.4.1 | INELIGIBLE | E1: WebSocket transport. |
| 85 | V11.3.4 | INELIGIBLE | E1: nonce/IV management for encryption algorithms. |
| 86 | V4.1.2 | INELIGIBLE | E1: HTTP-to-HTTPS redirects (transport). |
| 87 | V14.2.7 | INELIGIBLE | E4: no retention period exists for a test to hold an implementation to unless the request states one. |
| 88 | V2.1.3 | INELIGIBLE | E1/E2: business-logic limits documentation. |
| 89 | V11.2.3 | INELIGIBLE | E1: cryptographic strength / key size choice. |
| 90 | V1.3.5 | ELIGIBLE | Task: let admins write product descriptions in a lightweight markup rendered to HTML for the listing; test submits a description containing script/markup and checks the rendered output neutralises it. |
| 91 | V10.3.2 | INELIGIBLE | E1: OAuth delegated-authorization claims. |
| 92 | V6.5.4 | ELIGIBLE | Task: add emailed one-time login codes; test generates many codes and checks their length and alphabet give at least the required entropy (e.g. not 4-digit PINs). |
| 93 | V3.3.1 | INELIGIBLE | E1: browser cookie attributes. |
| 94 | V4.4.2 | INELIGIBLE | E1: WebSocket handshake origin. |
| 95 | V6.6.3 | ELIGIBLE | Task: add emailed one-time login codes; test submits many wrong codes for one account and then the correct one, and checks further guessing is blocked by an attempt limit. |
| 96 | V8.3.1 | INELIGIBLE | E3: README 4 already requires handlers to enforce permissions server-side with require(). |
| 97 | V10.5.5 | INELIGIBLE | E1: OIDC back-channel logout. |
| 98 | V10.4.8 | INELIGIBLE | E1: OAuth refresh tokens (authorization-server internals). |
| 99 | V4.3.1 | INELIGIBLE | E1: GraphQL. |
| 100 | V12.3.1 | INELIGIBLE | E1/E2: TLS for all connections. |
| 101 | V1.2.6 | INELIGIBLE | E1: LDAP is absent. |
| 102 | V7.1.1 | INELIGIBLE | E1/E2: session documentation. |
| 103 | V4.2.4 | INELIGIBLE | E1: HTTP/2-3 header framing. |
| 104 | V13.1.4 | INELIGIBLE | E1/E2: secrets rotation documentation. |
| 105 | V2.4.1 | ELIGIBLE | Task: add a handler that lets customers check whether a coupon code is valid; test fires a very large burst of calls from one caller at one shop-clock instant and checks later calls are refused. |
| 106 | V3.2.2 | INELIGIBLE | E1: browser DOM rendering functions. |
| 107 | V16.2.3 | INELIGIBLE | E1/E2: log destinations vs log inventory documentation. |
| 108 | V7.6.2 | INELIGIBLE | E1: federated session creation consent. |
| 109 | V5.1.1 | INELIGIBLE | E1/E2: upload documentation. |
| 110 | V6.2.9 | INELIGIBLE | E3: base already accepts any password length from 12 up. |
| 111 | V11.1.4 | INELIGIBLE | E1/E2: cryptographic inventory documentation. |
| 112 | V6.2.10 | INELIGIBLE | E4: a straightforward implementation does not add forced rotation unless asked. |
| 113 | V16.2.4 | INELIGIBLE | E1/E3: log processor format; events are already uniform dicts. |
| 114 | V15.2.2 | ELIGIBLE | Task: add a paginated order search/report handler with a caller-chosen page size or date range; test asks for an enormous page or range and checks it is capped or rejected rather than served in full. |

screened 114 ids, 20 eligible
