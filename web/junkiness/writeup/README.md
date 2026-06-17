# Junkiness

## Overview
This challenge is an extremely basic Node.js/Express application with only 3 endpoints:
- An endpoint to register (`/register`)
- An endpoint to login (`/login`)
- An endpoint to get the flag, if the user is an admin (`/flag`)

## Vulnerability
This application is vulnerable to server-side prototype pollution.  
```js
users[username] = { username, password, isAdmin: false };
```

## Solution
If `username` is set to `__proto__`, the prototype of the `users` object will be overridden with user-provided data. However `__proto__` is 9 characters long, therefore it won't pass this check:
```js
if (username.length > 8) {
    return res.status(400).json({ message: "Username must not be longer than 8 characters." });
}
```
To get around this, it's possible to abuse JavaScript type coercion: in many situations input data is converted into a string using the `.toString()` method before being processed. If `username` were to be an array, it would easily pass the length check.  
However, note that it must be an array with exactly one element, otherwise elements would get joined with `, ` and the exploit would not work. To make this clearer to those playing the challenge, I added a regex check that allows only alphanumeric characters:
```js
if (/\W/.test(username)) {
    return res.status(400).json({ message: "Username must be an alphanumeric string." });
}
```
How do you pass arrays to the api endpoint though?
```js
app.use(express.urlencoded({ extended: true }));
```
This Express middleware makes it so body fields like `password[]=test` are parsed as an array (`password`=`["test"]`) and body fields like `password[prop]=test` are parsed as an object (`password`=`{prop:"test"}`).  

Now that I've explained how to achieve prototype pollution, let's see what data to send for the exploit:
- First send a POST request to `/register` with the following data: `username[]=__proto__&password[isAdmin]=1&password[password]=gg`. The server will parse this as `{username: ["__proto__"], password: {isAdmin: "1", "password": "gg"}}` (note that `1` can be any truthy value and `gg` is an arbitrary string). Because of the prototype pollution, this will effectively create a user with admin privileges named `password`, whose password is `gg`.
- Then send a POST request to `/login` with `username=password&password=gg`. This will log you in as a user with admin privileges.
- Finally, send a GET request to `/flag` to get the flag.
