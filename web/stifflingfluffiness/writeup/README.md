# StifflingFluffiness

## Overview
This application represents a simple blog. Users can log in with any username, without needing a password, though the length of the username must be between 4 and 12 characters.  
The flag is hidden inside a comment under the first blog post. However, only the admin user (whose username is StifflingFluffiness) is able to see comments.

## Vulnerability
The length of the username of the admin is 19 characters, therefore it's too long for the login form.

Notice how the comparison between the user-provided username and the admin username is done case-insensitively by converting both to upper case first:
```js
req.session.isAdmin = username.toUpperCase() === ADMIN_USERNAME.toUpperCase();
```

In JavaScript, as in many other programming languages, string case conversion follows the Unicode Default Case Conversion algorithm (https://tc39.es/ecma262/multipage/text-processing.html#sec-string.prototype.tolowercase).
The first note in that section of the spec explicitly says
> The case mapping of some code points may produce multiple code points. In this case the result String may not be the same length as the source String. Because both toUpperCase and toLowerCase have context-sensitive behaviour, the methods are not symmetrical. In other words, s.toUpperCase().toLowerCase() is not necessarily equal to s.toLowerCase().

A text file located at https://unicode.org/Public/UCD/latest/ucd/SpecialCasing.txt contains all the characters that turn into multiple characters when converted to uppercase.  
In particular:  
`ﬆ` -> `ST`  
`ﬄ` -> `FFL`  
`ﬂ` -> `FL`  
`ﬃ` -> `FFI`  
`ß` -> `SS`  
This allows bypassing the length restrictions on the username.

## Solution
Construct a username that becomes 'STIFFLINGFLUFFINESS' when converted to uppercase using ligatures: `ﬆiﬄingﬂuﬃneß` (12 characters long).
```js
"ﬆiﬄingﬂuﬃneß".toUpperCase() === "StifflingFluffiness".toUpperCase() // true
"ﬆiﬄingﬂuﬃneß".length // 12
```
