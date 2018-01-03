const path = require("path");

const ZipPlugin = require("zip-webpack-plugin");

module.exports = {
    entry: {
        handler: path.resolve(__dirname, "handler.js"),
    },
    externals: [
        "aws-sdk", // included in Lambda by default
    ],
    output: {
        path: path.resolve(__dirname, "dist"),
        library: "[name]",
        libraryTarget: "umd",
        filename: "[name].js",
    },
    resolve: {
        alias: {underscore: "lodash"},
    },
    target: "node",
    module: {
        noParse: [/node_modules\/redis-parser\/lib\/hiredis\.js/],
        rules: [
            {
                test: /\.js$/,
                use: ["shebang-loader", "babel-loader"],
            },
        ],
    },
    plugins: [
        new ZipPlugin({
            filename: "lambda.zip",
        }),
    ],
};
