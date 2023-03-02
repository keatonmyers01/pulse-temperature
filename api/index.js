const express = require('express');
const mysql = require('mysql');
const cors = require('cors');
var fs = require('fs');

//fill in your db information 
const db = mysql.createConnection({
    host: '',
    user: '',
    password: '',
    database: ''
});

db.connect((err) => {
    if(err){
        throw err
    }
    console.log('connected');
});


const app = express();
app.use(express.json());

//running it on 3001 since I'm also hosting a graphana instance to handle graphing
const PORT = process.env.PORT || 3001;

app.get('/',(req, res) => {
    console.log("recived get")
    res.json('api is working')
});

function subtractSeconds(date, seconds) {
    // make copy with Date() constructor
    const dateCopy = new Date(date);
  
    dateCopy.setSeconds(date.getSeconds() - seconds);
  
    return dateCopy;
};

//saves sent data to the db, time is calculated based on diffrence in record time and the time the data was transmitted
app.post('/new_data', (req, res) => {
    if(!req.body){
        console.log("no body");
        return res.sendStatus(200);
    };

    if(req.body["beats"].length == 0 || req.body["temps"].length == 0){
        console.log("no records");
        return res.sendStatus(200);
    }

    console.log("reciving data");
    console.log(req.body)

    var recived_time = new Date();
    var query_temp = `INSERT INTO temperature (
        temperature,
        time
    )
    VALUES`
    var query_heart = `INSERT INTO heart_rate (
        bpm,
        time
    )
    VALUES`

    for(var i = 0; i < req.body["beats"].length; i++){
        query_temp += `(
            ${req.body["temps"][i]["temps"]},
            "${subtractSeconds(recived_time, req.body["transmission_time"] - req.body["temps"][i]["time"]).toISOString().slice(0, 19).replace('T', ' ')}"
        ),`

        query_heart += `(
            ${req.body["beats"][i]["bpm"]},
            "${subtractSeconds(recived_time, req.body["transmission_time"] - req.body["beats"][i]["time"]).toISOString().slice(0, 19).replace('T', ' ')}"
        ),`
    }

    query_heart = query_heart.slice(0,-1)
    query_temp = query_temp.slice(0,-1)


    db.query(query_temp, (err, result) => {
        if(err) throw err
        db.query(query_heart, (err, result) => {
            if(err) throw err
            return res.status(200).send(result)
            
        })
    })
});

//saves a log file to the 
app.post('/new_log', (req, res) => {
    
    if(!req.body){
        console.log("no body");
        return res.sendStatus(200);
    };

    fs.writeFile( "../../logs/" + req.body["name"], req.body["content"], (err) => {
        if (err) throw err;
    });

    return res.sendStatus(200)
});

app.listen(PORT, () => console.log(`Server listening in port ${PORT}`))