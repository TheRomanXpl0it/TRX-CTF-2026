import express from "express";
import session from "express-session";
import path from "path";
import { SECRET, ADMIN_USERNAME, MAIN_COLOR, BACKGROUND_COLOR } from "./config.js";

const FLAG = process.env.FLAG || "TRX{fake_flag}";
const PORT = process.env.PORT || 3000;

const app = express();

app.set("view engine", "ejs");
app.set("views", path.join(import.meta.dirname, "views"));
app.use(express.urlencoded());
app.use(
    session({
        secret: SECRET,
        resave: false,
        saveUninitialized: true,
    }),
);

const posts = [
    {
        id: 1,
        title: "Welcome to the blog!",
        content: "I hope you'll like my fluffy posts.",
        comments: [
            { user: "PinkSheep", text: "Nice blog!" },
            { user: ADMIN_USERNAME, text: `Thank you! Here is the flag: ${FLAG}` },
        ],
    },
    {
        id: 2,
        title: "Second Post",
        content: "Stay tuned for more updates.",
        comments: [{ user: "WoolooLover", text: "Looking forward to that!" }],
    },
];

app.get("/", (req, res) => {
    const username = req.session.username;
    const error = req.session.error;
    delete req.session.error;

    res.render("index", {
        admin_username: ADMIN_USERNAME,
        main_color: MAIN_COLOR,
        background_color: BACKGROUND_COLOR,
        username,
        error,
        posts: posts.map(post => ({
            ...post,
            comments: req.session.isAdmin ? post.comments : undefined,
        })),
    });
});

app.post("/login", (req, res) => {
    const { username } = req.body;

    if (!username || username.length < 4 || username.length > 12) {
        req.session.error = "Invalid username";
        return res.redirect("/");
    }

    req.session.username = username;
    req.session.isAdmin = username.toUpperCase() === ADMIN_USERNAME.toUpperCase();
    res.redirect("/");
});

app.post("/logout", (req, res) => {
    req.session.destroy(() => {
        res.redirect("/");
    });
});

app.listen(PORT, () => {
    console.log(`Server running on http://0.0.0.0:${PORT}`);
});
