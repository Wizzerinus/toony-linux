# Toony Linux

A minimalistic Linux launcher for Toontown Rewritten and Toontown: Corporate Clash.

## Configuration

* Copy `accounts.example.yaml` to `accounts.yml` and fill in your account details.
  (multiple toons are supported)
* If using Corporate Clash: install it via Wine and the launcher and launch the game
  once. That way the script can find the installation path correctly
* Run the script
* If using Toontown Rewritten: Use `update` command to download the game
* Run `lc <toon1> <toon2>`
* Optional: `ds <district>` to set the district for newly-spawned Clash toons.

### Disclaimer: Password encryption
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