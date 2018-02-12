// File used to send large amounts of requests to a http location
// Can send multiple requests at the same time (set step for that)

const fs = require('fs');
const https = require('https');

// All the presets here
// Reads from a specified file all previously parsed information. Saves all the information (old + new) to the
// save file. Sends all request to url.
// You can read and save to the same file, but this is not recommended, because all the information will be lost
// if program crashes while writing to file.
const read_from = 'geocodes.list';
const save_to = 'geocodes2.list';
// const url = 'https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates' +
//              '?f=json&outFields=Match_addr,Addr_type&singleLine=';
const url = 'https://maps.googleapis.com/maps/api/geocode/json?address=';
const step = 10;

const readyLocations = {};
const locations = {};
let locationsLength;
const errors = [];

function readResults(){
    // function reads from read_from file and saves to readyLocations array
    let file = fs.createReadStream(read_from, 'utf-8');
    let data = '';

    file.on('data', (text) => {
        data += text;
    });

    file.on('end', () => {
        data = data.split('\n');
        for(let item of data){
            item = item.split('\t');
            if(item[1] && item[2] && item[1] != 'undefined' && item[2] != 'undefined')
                readyLocations[item[0]] = [item[1], item[2]];
        }

        console.log('Found locations: ', Object.keys(readyLocations).length);
        readFilms();
    });
}

function readFilms() {
    // finds more locations in 'locations.list' and saves to locations array
    const file = fs.createReadStream('locations.list', 'utf-8');
    let data = '';

    file.on('data', (text) => {
        data += text;
    });

    file.on('end', () => {
        data = data.split('\n');

        for (let item of data) {
            item = item.split('\t');

            // skip first few lines
            if (item.length > 1) {
                let location;
                if (item[item.length - 1][0] == '(')
                    location = item[item.length - 2];
                else
                    location = item[item.length - 1];

                // add if location does not exist yet
                if (!(location in locations || location in readyLocations)) {
                    // console.log('Reading file. Current location: ' + location);
                    locations[location] = [];
                }
            }
        }
        parseLocations(0);
    });
}

function parseLocation(location, last, onLast){
    let dataString = '';
        try {
            let request = https.request(url + location, (res) => {
                res.setEncoding('utf-8');

                res.on('data', (data) => {
                    try {
                        dataString += data;
                    }
                    catch (error) {
                        console.log(error);
                    }
                });

                res.on('end', () => {
                    try {
                        let jsonObj = JSON.parse(dataString);

                        // json.candidates[0].location.x | .y for ArcGIS
                        // json.results[0].geometry.location.lng | .lat
                        if (jsonObj && 'results' in jsonObj) {
                            let coords = jsonObj.results[0].geometry.location;

                            locations[location] = [coords.lng, coords.lat];
                            // console.log('response for: ' + location);
                            // console.log(coords);
                        }

                        // if last
                        if (location === last)
                            onLast();
                    }
                    catch (error) {
                        console.log(error);
                        errors.push(location);

                        // if last
                        if (location === last)
                            onLast();
                    }
                });

                res.on('error', (error) => {
                    console.log(error);
                    errors.push(location);
                });
            });

            request.on('error', (error) => {
                console.log(error);
                errors.push(location);

                // if last
                if (location === last)
                    onLast();
            });

            request.end();
        }
        catch(error){
            console.log(error);
            errors.push(location);
        }
}

function parseLocations(i_min){
    if(!locationsLength){
        locationsLength = Object.keys(locations).length;
    }

    console.log('Requests done: ' + i_min + ' / ' + locationsLength, 'Errors: ', errors.length);
    if(i_min % 500 === 0){
        writeFile();
    }
    if(i_min >= locationsLength) {
        console.log('All requests done');
        writeFile();
        console.log(errors);
    }
    let i_max = i_min + step;

    currentSlice = Object.keys(locations).slice(i_min, i_max);
    for(let item of currentSlice) {
        parseLocation(item, currentSlice[currentSlice.length - 1], parseLocations.bind(this, i_min + step))
    }
}

function writeFile(){
    console.log('Writing to file!');
    const file = fs.createWriteStream(save_to, 'utf-8');

    let result = '';
    for(let item in readyLocations)
        if(readyLocations[item][0] && readyLocations[item][1])
            result += item + '\t' + readyLocations[item][0] + '\t' + readyLocations[item][1] + '\n';

    for(let item in locations)
        if(locations[item][0] && locations[item][1])
            result += item + '\t' + locations[item][0] + '\t' + locations[item][1] + '\n';

    file.write(result);
    file.close()
}

// start the program
readResults();