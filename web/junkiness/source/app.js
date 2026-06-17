const express = require("express");
const session = require("express-session");
const crypto = require("crypto");
const path = require("path");

const FLAG = process.env.FLAG || "TRX{fake_flag}";
const PORT = process.env.PORT || 3000;
const SECRET = crypto.randomBytes(24).toString("hex");

const app = express();

app.use(
    session({
        secret: SECRET,
        resave: false,
        saveUninitialized: true,
        cookie: { secure: false },
    }),
);
app.use(express.urlencoded({ extended: true }));
app.use(express.static(path.join(__dirname, "public")));

const users = {};

app.post("/register", (req, res) => {
    if (!req.body) {
        return res.status(400).json({ message: "Invalid request." });
    }

    const { username, password } = req.body;

    if (!username || !password) {
        return res.status(400).json({ message: "Username and password required." });
    }

    if (username.length > 8) {
        return res.status(400).json({ message: "Username must not be longer than 8 characters." });
    }

    if (/\W/.test(username)) {
        return res.status(400).json({ message: "Username must be an alphanumeric string." });
    }

    if (Object.keys(users).includes(username)) {
        return res.status(409).json({ message: "User already exists." });
    }

    users[username] = { username, password, isAdmin: false };
    res.status(201).json({ message: "User registered successfully." });
});

app.post("/login", (req, res) => {
    if (!req.body) {
        return res.status(400).json({ message: "Invalid request." });
    }

    const { username, password } = req.body;

    if (!username || !password) {
        return res.status(400).json({ message: "Username and password required." });
    }

    const user = users[username];

    if (!user) {
        return res.status(404).json({ message: "User not found." });
    }

    if (user.password !== password) {
        return res.status(401).json({ message: "Invalid password." });
    }

    req.session.user = user;
    res.json({ message: "Login successful." });
});

app.get("/flag", (req, res) => {
    if (req.session.user && req.session.user.isAdmin) {
        res.json(FLAG);
    } else {
        res.status(403).json({ message: "Forbidden: Admins only." });
    }
});

app.post("/logout", (req, res) => {
    req.session.destroy(() => {
        res.json({ message: "Logged out." });
    });
});

app.listen(PORT, () => {
    console.log(`Server running on http://0.0.0.0:${PORT}`);
});
