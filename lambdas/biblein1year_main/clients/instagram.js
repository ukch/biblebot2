const path = require("path");

const Client = require("instagram-private-api").V1;
const request = require("request");

const config = require("../config.json").instagram;

class Instagram {
    constructor() {
        const device = new Client.Device(config.username);
        const storage = new Client.CookieFileStorage(path.join(__dirname, `../cookies/${config.username}.json`));
        this.session = Client.Session.create(device, storage, config.username, config.password);
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
}
Instagram.instance = null;

module.exports = Instagram;
