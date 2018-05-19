const DynamoDB = require("aws-sdk").DynamoDB;
const htmlToText = require("html-to-text");
const request = require("request-promise-native");
const marshaler = require("dynamodb-marshaler");
const quotation = require("quotation");

const marshalItem = marshaler.marshalItem;
const unmarshalItem = marshaler.unmarshalItem;
const dynamodb = new DynamoDB({apiVersion: "2012-08-10", region: "eu-west-1"});

const URL_PATTERN = "http://ref.ly/";

function _p(wrappedFunc) {
    // Promisify the function
    return new Promise((resolve, reject) => {
        wrappedFunc((err, result) => {
            if (err) {
                return reject(err);
            }
            return resolve(result);
        });
    });
}

async function elongateReference(ref) {
    const regex = /[0-9]/;
    let parts = ref.split(regex);
    var bookShort = parts[0].trim();
    if (!bookShort) {
        let number = ref.match(regex)[0];
        bookShort = `${number} ${parts[1].trim()}`;
    }
    var params = {
        TableName: "abbreviations",
        Key: marshalItem({
            book_short: bookShort.toLowerCase(),
        }),
    };
    var result = await dynamodb.getItem(params).promise();
    if (!result.Item) {
        console.warn(`No short reference found for ${bookShort}`);
        return ref;
    }
    var book = unmarshalItem(result.Item).book;
    return ref.replace(bookShort, book);
}

function getUrl(ref) {
    ref = ref.replace(/:/g, ".").replace(/\s/g, "");
    return URL_PATTERN + encodeURIComponent(ref);
}

async function getVerses(ref) {
    /* Call the bible.org API to fetch the verses */
    let url = `http://labs.bible.org/api/?formatting=full&type=json&passage=${ref}`;
    var response = await request({
        url: url,
        json: true,
    });
    return (function*() {
        for (let verse of response) {
            yield quotation(htmlToText.fromString(verse.text, {wordwrap: null}));
        }
    })();
}

module.exports = {
    marshalItem: marshalItem,
    unmarshalItem: unmarshalItem,
    dynamodb: dynamodb,
    "_p": _p,
    elongateReference: elongateReference,
    getUrl: getUrl,
    getVerses: getVerses,
};
