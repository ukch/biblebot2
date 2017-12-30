const DynamoDB = require("aws-sdk").DynamoDB;
const marshaler = require("dynamodb-marshaler");

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
    var bookShort = (ref.split(/[0-9]/)[0]).trim();
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
    ref = ref.replace(/:/g, ".").replace(" ", "");
    return URL_PATTERN + encodeURIComponent(ref);
}

module.exports = {
    marshalItem: marshalItem,
    unmarshalItem: unmarshalItem,
    dynamodb: dynamodb,
    "_p": _p,
    elongateReference: elongateReference,
    getUrl: getUrl,
};
