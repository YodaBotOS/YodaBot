// DO NOT CHANGE ANYTHING IN THIS FILE OR RENAME/REMOVE THIS FILE UNLESS YOU KNOW WHAT YOU ARE DOING!

const { parse } = require('twemoji-parser');

console.log(JSON.stringify(parse(process.argv[2])));