const fs = require("fs");
const path = require("path");

const Client = require("instagram-private-api").V1;
const request = require("request");
const S3 = require("aws-sdk").S3;

const _p = require("../tools")._p;
const config = require("../config.json").instagram;

const cookieDir = path.join(__dirname, "../cookies/");
const cookiePath = path.join(cookieDir, `${config.username}.json`);

class Instagram {
    async loadCookies() {
        var s3 = new S3();
        var response = await s3.getObject({
            Bucket: config.private_bucket_name,
            Key: `${config.username}.json`,
        }).promise();
        try {
            await _p(cb => fs.mkdir(cookieDir, cb));
        } catch (e) {
            if (e.code !== "EEXIST") {
                throw e;
            }
        }
        await _p(cb => fs.writeFile(cookiePath, response.Body, cb));
    }

    constructor() {
        const device = new Client.Device(config.username);
        const storage = new Client.CookieFileStorage(cookiePath);
        this.session = this.loadCookies().then(Client.Session.create(device, storage, config.username, config.password));
    }

    async post(imageUrl, verses, url, hashtags) {
        var imageStream = request(imageUrl)
            .on("response", response => {
                if (response.statusCode !== 200) {
                    throw new Error(response.statusCode, response.toJSON());
                }
            });
        var session = await this.session;
        var upload = await Client.Upload.photo(session, imageStream);
        let message = [
            (await verses).next().value,
            `Read more: ${url}`,
            hashtags.join(" "),
        ].join("\n\n");
        var data = await Client.Media.configurePhoto(session, upload.params.uploadId, message);
        console.log(data.id);
    }

    static post(imageUrl, verses, url, hashtags) {
        if (!this.instance) {
            this.instance = new this();
        }
        return this.instance.post(imageUrl, verses, url, hashtags);
    }

    static saveCookies() {
        var s3 = new S3();
        var fileStream = fs.createReadStream(cookiePath);
        return s3.putObject({
            Bucket: config.private_bucket_name,
            Key: `${config.username}.json`,
            Body: fileStream,
        }).promise();
    }
}
Instagram.instance = null;

module.exports = Instagram;
