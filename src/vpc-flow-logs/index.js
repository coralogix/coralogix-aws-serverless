'use strict';

console.log('Loading function');

const aws = require('aws-sdk');
const zlib = require('zlib');
const Coralogix = require("coralogix-logger");
const s3 = new aws.S3();
const assert = require('assert')
var newlinePattern = /(?:\r\n|\r|\n)/g;


assert(process.env.private_key, 'No private key')
const appName = process.env.app_name ? process.env.app_name : 'NO_APPLICATION';
const subName = process.env.sub_name ? process.env.sub_name : 'NO_SUBSYSTEM';


const config = new Coralogix.LoggerConfig({
    applicationName: appName,
    privateKey: process.env.private_key,
    subsystemName: subName,
});

Coralogix.CoralogixLogger.configure(config);

// create a new logger with category 
const logger = new Coralogix.CoralogixLogger('vpcflowlogs');


exports.handler = function (event, context, callback) {

    // Get the object from the event and show its content type
    const bucket = event.Records[0].s3.bucket.name;
    const key = decodeURIComponent(event.Records[0].s3.object.key.replace(/\+/g, ' '));
    const params = {
        Bucket: bucket,
        Key: key,
    };
    s3.getObject(params, (err, data) => {
        if (err) {
            console.log(err);
            callback(err);
        } else {
            if (data.ContentType == 'application/octet-stream' ||
                data.ContentType == 'application/x-gzip' ||
                data.ContentEncoding == 'gzip' ||
                data.ContentEncoding == 'compress' ||
                key.endsWith('.gz')) {

                zlib.gunzip(data.Body, function (error, result) {
                    if (error) {
                        context.fail(error);
                    } else {
                        sendLogs(Buffer.from(result))
                        callback(null, data.ContentType);
                    }
                });
            } else {
                sendLogs(Buffer.from(data.Body))
            }
        }
    });

    function sendLogs(content) {
        var logs =  content.toString('utf8').split(newlinePattern);

        console.log('numbers of logs:', logs.length)
        for (var i = 0; i < logs.length; i++) {
            // create a log
            if(!logs[i]) continue;
            const log = new Coralogix.Log({
                text: parseRecord(logs[i]),
                severity: 3
            })
            // send log to coralogix
            logger.addLog(log);
        }

    }

    function parseRecord(record) {
        const fields = [
            "version", "account-id", "interface-id", "srcaddr",
            "dstaddr", "srcport", "dstport", "protocol",
            "packets", "bytes", "start", "end",
            "action", "log-status"
        ];
        record = record.split(' ')
        return JSON.stringify(Object.assign(...fields.map((field, index) => ({ [field]: ((!isNaN(record[index])) ? parseInt(record[index]) : record[index]) }))))
    }
};
