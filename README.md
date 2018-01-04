# Bible Bot: The Next Generation
This is the new version of the original [Bible Bot](https://github.com/ukch/biblebot) that I wrote in order to Tweet a Bible reading plan. The new version is much expanded. At present it supports Instagram, but Twitter support is incoming.

Please feel free to modify this code to suit your own purposes.

## How it works:
This code assumes it will be ran on an AWS Lambda instance, using DynamoDB tables called `readings` and `abbreviations`. To get an up-and-running instance, you must do the following:

1. Create the above-named DynamoDB tables.
2. Populate your `readings` table with data in the following format:
   * Keys: `month` and `day` (numeric).
   * An entry is as follows: `{data: [{ref: 'Genesis 1:1'}, ...]}`. `ref` is fairly forgiving.
3. Populate the `abbreviations` table as necessary. Use the following format:
   * Keys: `book_short` (string)
   * An entry is as follows: `{book_short: 'gen', book: 'Genesis'}`. Please note `book_short` should always be lowercase.
4. [Correctly configure the AWS CLI.](https://docs.aws.amazon.com/cli/latest/userguide/cli-config-files.html)
5. (optional) To pre-populate images (for Instagram posting), run `./scripts/fetch_image_urls_for_month.py`. This fetches images for each ref in the given month from [Faithlife](https://bible.faithlife.com/).
6. (Instagram) Create an empty JSON file named `[your-instagram-username].json` and upload it to a private bucket on Amazon S3.
7. Get a Redis URL from somewhere.
8. Create a file `lambdas/biblein1year_main/config.json` in the following format:
```json
{
  "redis_url": "[Redis URL from step 7]",
  "instagram": {
    "username": "[Instagram username]",
    "password": "[Instagram password]",
    "private_bucket_name": "[S3 bucket name from step 6]"
  }
}
```
(Don't worry about storing the Instagram password in plain-text - after you have run the script for the first time, a cookie will be created and you can safely replace this with `null`.

9. Cd into `lambdas/biblein1year_main/config.json`, run `npm install`, then run `webpack`. This should create a file `./dist/lambda.zip`
10. Create your Lambda. When asked for the code, upload the zip file from step 9, and set the handler path to `handler.handler`.
11. Give the Lambda the following permissions:
    * The default Lambda permissions (log writing etc.)
    * DynamoDB: Permission to read both tables.
    * S3: `getObject` and `putObject` on the JSON file from step 6.
12. (optional) Test the Lambda using the `testMode: true` option (or the`--test`flag if running from command line)
13. (optional) To check for any upcoming concerns over the next 30 days, run `./scripts/find_problems.py`
