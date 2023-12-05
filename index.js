const express = require('express');
const path = require('path');
const app = express();

app.use(express.static("./"));

app.get('/', async(req, res) => {
    res.sendFile("./index.html");
});

app.listen(9090, () => {
    console.log("Server successfully running on port 9090");
  });