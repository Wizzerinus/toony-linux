# Toony Linux (v0.2)

A minimalistic Linux launcher for Toontown Rewritten and Toontown: Corporate Clash.

## Configuration

* Copy `accounts.example.yaml` to `accounts.yml` and fill in your account details.
  (multiple toons are supported)
* Run the script
* If using Corporate Clash: Use `update clash` command to download the game
* If using Toontown Rewritten: Use `update rewritten` command to download the game
* Run `lc <toon1> <toon2>` (can have any number of space-separated different toons)

### Disclaimer: Password encryption

***Note from 08/11/2022:*** Toontown: Corporate Clash implemented the token system and deprecated
password logins, so this does not apply to the server. It still applies to Toontown Rewritten, though.
***

As most Toontown login servers do not support login systems using 
asymmetric encryption algorithms, the passwords have to be stored in plain text.
This is a security risk. You can override this by *not setting your password*, which
will allow you to type in password at login time. As this launcher is open-source, it's
easy enough to check that I do not do more with your passwords than it is required to log
in, however, damage can be caused by people other than you opening the `accounts.yml` file.

**I am not responsible** for any damage caused by the plaintext password interface.
**You have been warned.** If you want better security, do not set the password in the file and enter it at login.

## TODO

* Graphical interface
* Multicontroller capabilities
* OCR and combo recognition
