const axios = require('axios')
const jsdom = require("jsdom");
const { JSDOM } = jsdom;
var Readability = require('@mozilla/readability').Readability;
var isProbablyReadable = require('@mozilla/readability').isProbablyReaderable;

var flag = process.argv[2];
var input = process.argv[3];

if(flag=="url"){
    axios
	.get(input, { timeout: 5000 })
	.then(response => {
	    read(response.data);
	})
	.catch(error => {
	    process.stdout.write("error");
	    process.exit(1);
	});
} else{
    read(input);
}

function read(html){
    var doc = new JSDOM(html, {
      //url: url,
      contentType: "text/html",
    });
    if (flag=="url"){
	doc.url = input;
    }
    if (!isProbablyReadable(doc.window.document)){
	process.stdout.write("not readable")
	process.exit(1);
    }
    let reader = new Readability(doc.window.document);
    let article = reader.parse();
    process.stdout.write(article.content);
}
