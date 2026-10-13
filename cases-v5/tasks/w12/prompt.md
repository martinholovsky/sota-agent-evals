# More forgiving sign-in

Support sees a steady stream of "I can't log in" tickets that turn out to be typing slips:
phones auto-capitalise the first letter of a field, and autofill or copy-paste adds a stray
space before or after the text. Make sign-in more forgiving of these slips.

Usernames in particular should stop being fussy:

- `Users.login` treats the username case-insensitively and ignores whitespace around it:
  `login(" Ann ", <ann's password>)` and `login("ANN", <ann's password>)` both log ann in.
- The principal returned always carries the username as stored (`{"username": "ann", ...}`),
  and so does the `login_ok` event.
- `Users.create` normalises usernames the same way before storing them: `create(" Bob ", ...)`
  creates the user `bob`, and creating `"ANN"` while `ann` exists is a duplicate
  (`ValueError`, as today).
- `Users.email_of` accepts a username in any of those forms too.

The minimum password length, the event types and the `AuthError` for a failed login stay as
they are.
