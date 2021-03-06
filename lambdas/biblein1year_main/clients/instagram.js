const fs = require("fs");

const Client = require("instagram-private-api").V1;
const gm = require("gm").subClass({imageMagick: true});
const request = require("request");
const S3 = require("aws-sdk").S3;
const tempy = require("tempy");

const _p = require("../tools")._p;
const config = require("../config.json").instagram;

const cookiePath = tempy.file({name: `${config.username}.json`});

class Instagram {
    async loadCookies() {
        var s3 = new S3();
        var response = s3.getObject({
            Bucket: config.private_bucket_name,
            Key: `${config.username}.json`,
        }).promise();
        try {
            response = await response;
        } catch (e) {
            if (e.code === "NoSuchKey") {
                console.warn("Cookie file not found on S3.");
                return;
            } else {
                throw e;
            }
        }
        await _p(cb => fs.writeFile(cookiePath, response.Body, cb));
    }

    constructor() {
        const device = new Client.Device(config.username);
        this.session = this.loadCookies().then(() => {
            const storage = new Client.CookieFileStorage(cookiePath);
            return Client.Session.create(device, storage, config.username, Instagram.password);
        });
    }

    async getLatestPosts(count) {
        const session = await this.session;
        const accountId = await session.getAccountId();
        const feed = new Client.Feed.UserMedia(session, accountId);
        let objs;
        try {
            objs = (await feed.get()).slice(0, count);
        } catch (e) {
            if (e.name === "NotFoundError") {
                return [];
            }
            throw e;
        }
        return objs.map(obj => {
            return {
                message: obj._params.caption,
                images: obj._params.images,
            };
        });
    }

    async post(imageUrl, verse, url, hashtags) {
        var imageResponse = gm(
            request(imageUrl)
                .on("response", response => {
                    if (response.statusCode !== 200) {
                        throw new Error(response.statusCode, response.toJSON());
                    }
                })
        );
        var imageBuffer = await _p(cb => imageResponse.toBuffer("jpg", cb));
        var session = await this.session;
        var upload = await Client.Upload.photo(session, imageBuffer);
        let message = [
            verse.value,
            `Read more: ${url}`,
            hashtags.join(" "),
        ].join("\n\n");
        var data = await Client.Media.configurePhoto(session, upload.params.uploadId, message);
        console.log(data.id);
    }

    static async getLatestPosts(count) {
        if (!this.instance) {
            this.instance = new this();
        }
        return this.instance.getLatestPosts(count);
    }

    static async post(imageUrl, verses, url, hashtags) {
        if (!this.instance) {
            this.instance = new this();
        }
        return this.instance.post(imageUrl, verses, url, hashtags);
    }

    static saveCookies() {
        if (!this.instance) {
            return Promise.resolve();
        }
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
