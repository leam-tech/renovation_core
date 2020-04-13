/**
 * THE CODE BELOW IS COPIED FROM FRAPPE
 * Wherever a change is made, a comment with 'renovation_core' is included
 */

var app = require('express')();
var server = require('http').Server(app);
var io = require('socket.io')(server, {
    handlePreflightRequest: function (req, res) {
        var headers = {
            'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Client-Site',
            'Access-Control-Allow-Origin': req.headers.origin,
            'Access-Control-Allow-Credentials': true
        };
        res.writeHead(200, headers);
        res.end();
    }
});
var cookie = require('cookie')
var fs = require('fs');
var path = require('path');
var request = require('superagent');

/**
 * FRAPPE node_utils
 */
const redis = require('redis');
const bench_path = path.resolve(__dirname, '..', '..');

function get_conf() {
    // defaults
    var conf = {
        redis_async_broker_port: 12311,
        socketio_port: 3000
    };

    var read_config = function (file_path) {
        const full_path = path.resolve(bench_path, file_path);

        if (fs.existsSync(full_path)) {
            var bench_config = JSON.parse(fs.readFileSync(full_path));
            for (var key in bench_config) {
                if (bench_config[key]) {
                    conf[key] = bench_config[key];
                }
            }
        }
    }

    // get ports from bench/config.json
    read_config('config.json');
    read_config('sites/common_site_config.json');

    // detect current site
    if (fs.existsSync('sites/currentsite.txt')) {
        conf.default_site = fs.readFileSync('sites/currentsite.txt').toString().trim();
    }

    return conf;
}

function get_redis_subscriber() {
    const conf = get_conf();
    const host = conf.redis_socketio || conf.redis_async_broker_port;
    return redis.createClient(host);
}

/**
 * node_utils END
 */


var conf = get_conf();
var flags = {};
var files_struct = {
    name: null,
    type: null,
    size: 0,
    data: [],
    slice: 0,
    site_name: null,
    is_private: 0
};

var subscriber = get_redis_subscriber();

// serve socketio
server.listen(conf.socketio_port, function () {
    console.log('listening on *:', conf.socketio_port); //eslint-disable-line
});

// on socket connection
io.on('connection', async function (socket) {
    // [renovation_core] We have many cases when host and origin doesnt match
    // if (get_hostname(socket.request.headers.host) != get_hostname(socket.request.headers.origin)) {
    // 	return;
    // }

    // [renovation_core] We have many cases when there are no cookies
    // if (!socket.request.headers.cookie) {
    //   return;
    // }
    // var sid = cookie.parse(socket.request.headers.cookie || "").sid
    // if (!sid) {
    // 	return;
    // }

    const {user, sid, ...userDetails} = await getRenovationUserDetails(socket);

    socket.user = user;
    socket.files = {};

    if (user !== "Guest") {
        var room = get_user_room(socket, user);
        socket.join(room);
        socket.join(get_site_room(socket));
        socket.send(`Joining SiteRoom: ${get_site_room(socket)}`);
        socket.send(`Joining User Room: ${user}`);
        io.to(room).emit("socket-frappe-connection", {
            user: user
        });
    } else {
        if (userDetails && userDetails.allow_guest) {
            socket.send("Joining Guest-User Room");
            socket.join(get_user_room(socket, user))
        }
    }

    // frappe.chat
    socket.on("frappe.chat.room:subscribe", function (rooms) {
        if (!Array.isArray(rooms)) {
            rooms = [rooms];
        }

        for (var room of rooms) {
            console.log('frappe.chat: Subscribing ' + socket.user + ' to room ' + room);
            room = get_chat_room(socket, room);

            console.log('frappe.chat: Subscribing ' + socket.user + ' to event ' + room);
            socket.join(room);
        }
    });

    socket.on("frappe.chat.message:typing", function (data) {
        const user = data.user;
        const room = get_chat_room(socket, data.room);

        console.log('frappe.chat: Dispatching ' + user + ' typing to room ' + room);

        io.to(room).emit('frappe.chat.room:typing', {
            room: data.room,
            user: user
        });
    });
    // end frappe.chat

    // [renovation_core] getRenovationUserDetails obsoletes this
    // request.get(get_url(socket, '/api/method/frappe.realtime.get_user_info'))
    // 	.set({'X-Client-Site': get_site_name(socket)})
    // 	.type('form')
    // 	.query({
    // 		sid: sid
    // 	})
    // 	.end(function (err, res) {
    // 		if (err) {
    // 			console.log(err);
    // 			console.log(get_hostname(socket.request.headers.host), get_hostname(socket.request.headers.origin))
    // 			console.log("Failed to get user info", "sid", sid);
    // 			console.log("Sitename", get_site_name(socket));
    // 			return;
    // 		}
    // 		if (res.status == 200) {
    // 			var room = get_user_room(socket, res.body.message.user);
    // 			socket.join(room);
    // 			socket.join(get_site_room(socket));
    // 			console.log("Socket joined rooms", room, get_site_room(socket));
    // 		}
    // 	});

    socket.on('disconnect', function () {
        delete socket.files;
    })

    socket.on('task_subscribe', function (task_id) {
        var room = get_task_room(socket, task_id);
        socket.join(room);
    });

    socket.on('task_unsubscribe', function (task_id) {
        var room = get_task_room(socket, task_id);
        socket.leave(room);
    });

    socket.on('progress_subscribe', function (task_id) {
        var room = get_task_room(socket, task_id);
        socket.join(room);
        send_existing_lines(task_id, socket);
    });

    socket.on('doc_subscribe', function (doctype, docname) {
        can_subscribe_doc({
            socket: socket,
            sid: sid,
            doctype: doctype,
            docname: docname,
            callback: function (err, res) {
                var room = get_doc_room(socket, doctype, docname);
                socket.join(room);
            }
        });
    });

    socket.on('doc_unsubscribe', function (doctype, docname) {
        var room = get_doc_room(socket, doctype, docname);
        socket.leave(room);
    });

    socket.on('task_unsubscribe', function (task_id) {
        var room = 'task:' + task_id;
        socket.leave(room);
    });

    socket.on('doc_open', function (doctype, docname) {
        // show who is currently viewing the form
        can_subscribe_doc({
            socket: socket,
            sid: sid,
            doctype: doctype,
            docname: docname,
            callback: function (err, res) {
                var room = get_open_doc_room(socket, doctype, docname);
                socket.join(room);

                send_viewers({
                    socket: socket,
                    doctype: doctype,
                    docname: docname,
                });
            }
        });
    });

    socket.on('doc_close', function (doctype, docname) {
        // remove this user from the list of 'who is currently viewing the form'
        var room = get_open_doc_room(socket, doctype, docname);
        socket.leave(room);
        send_viewers({
            socket: socket,
            doctype: doctype,
            docname: docname,
        });
    });

    socket.on('upload-accept-slice', (data) => {
        try {
            if (!socket.files[data.name]) {
                socket.files[data.name] = Object.assign({}, files_struct, data);
                socket.files[data.name].data = [];
            }

            //convert the ArrayBuffer to Buffer
            data.data = new Buffer(new Uint8Array(data.data));
            //save the data
            socket.files[data.name].data.push(data.data);
            socket.files[data.name].slice++;

            if (socket.files[data.name].slice * 24576 >= socket.files[data.name].size) {
                // do something with the data
                var fileBuffer = Buffer.concat(socket.files[data.name].data);

                const file_url = path.join((socket.files[data.name].is_private ? 'private' : 'public'),
                    'files', data.name);
                const file_path = path.join('sites', get_site_name(socket), file_url);

                fs.writeFile(file_path, fileBuffer, (err) => {
                    delete socket.files[data.name];
                    if (err) return socket.emit('upload error');
                    socket.emit('upload-end', {
                        file_url: '/' + file_url
                    });
                });
            } else {
                socket.emit('upload-request-slice', {
                    currentSlice: socket.files[data.name].slice
                });
            }
        } catch (e) {
            console.log(e);
            socket.emit('upload-error', {
                error: e.message
            });
        }
    });
});

subscriber.on("message", function (channel, message, room) {
    message = JSON.parse(message);

    if (message.room) {
        io.to(message.room).emit(message.event, message.message);
    } else {
        io.emit(message.event, message.message);
    }
});


subscriber.subscribe("events");

function send_existing_lines(task_id, socket) {
    var room = get_task_room(socket, task_id);
    subscriber.hgetall('task_log:' + task_id, function (err, lines) {
        io.to(room).emit('task_progress', {
            "task_id": task_id,
            "message": {
                "lines": lines
            }
        });
    });
}

function get_doc_room(socket, doctype, docname) {
    return get_site_name(socket) + ':doc:' + doctype + '/' + docname;
}

function get_open_doc_room(socket, doctype, docname) {
    return get_site_name(socket) + ':open_doc:' + doctype + '/' + docname;
}

function get_user_room(socket, user) {
    return get_site_name(socket) + ':user:' + user;
}

function get_site_room(socket) {
    return get_site_name(socket) + ':all';
}

function get_task_room(socket, task_id) {
    return get_site_name(socket) + ':task_progress:' + task_id;
}

// frappe.chat
// If you're thinking on multi-site or anything, please
// update frappe.async as well.
function get_chat_room(socket, room) {
    var room = get_site_name(socket) + ":room:" + room;

    return room
}

function get_site_name(socket) {
    if (socket.request.headers['x-frappe-site-name']) {
        return get_hostname(socket.request.headers['x-frappe-site-name']);
    } else if (['localhost', '127.0.0.1'].indexOf(socket.request.headers.host) !== -1 &&
        conf.default_site) {
        // from currentsite.txt since host is localhost
        return conf.default_site;
    } else if (socket.request.headers.origin) {
        return get_hostname(socket.request.headers.origin);
    } else {
        return get_hostname(socket.request.headers.host);
    }
}

function get_hostname(url) {
    if (!url) return undefined;
    if (url.indexOf("://") > -1) {
        url = url.split('/')[2];
    }
    return (url.match(/:/g)) ? url.slice(0, url.indexOf(":")) : url
}

function get_url(socket, path) {
    if (!path) {
        path = '';
    }
    // [renovation_core]
    // Originally this was request.header.origin
    // Since we do cross domain requests, Host is the way to go
    // return socket.request.headers.host + path;
    if (get_hostname(socket.request.headers.origin) === get_hostname(socket.request.headers.host)) {
        return socket.request.headers.origin + path;
    } else {
        // fetch http scheme from origin and apply on host
        const https = (socket.request.headers.origin || "").indexOf("https") > -1;
        return `http${https ? "s" : ""}://${socket.request.headers.host}${path}`
    }
}

function can_subscribe_doc(args) {
    if (!args) return;
    if (!args.doctype || !args.docname) return;
    request.get(get_url(args.socket, '/api/method/frappe.realtime.can_subscribe_doc'))
        .type('form')
        .query({
            sid: args.sid,
            doctype: args.doctype,
            docname: args.docname
        })
        .end(function (err, res) {
            if (!res) {
                console.log("No response for doc_subscribe");

            } else if (res.status == 403) {
                return;

            } else if (err) {
                console.log(err);

            } else if (res.status == 200) {
                args.callback(err, res);

            } else {
                console.log("Something went wrong", err, res);
            }
        });
}

function send_viewers(args) {
    // send to doc room, 'users currently viewing this document'
    if (!(args && args.doctype && args.docname)) {
        return;
    }

    // open doc room
    var room = get_open_doc_room(args.socket, args.doctype, args.docname);

    var socketio_room = io.sockets.adapter.rooms[room] || {};

    // for compatibility with both v1.3.7 and 1.4.4
    var clients_dict = ("sockets" in socketio_room) ? socketio_room.sockets : socketio_room;

    // socket ids connected to this room
    var clients = Object.keys(clients_dict || {});

    var viewers = [];
    for (var i in io.sockets.sockets) {
        var s = io.sockets.sockets[i];
        if (clients.indexOf(s.id) !== -1) {
            // this socket is connected to the room
            viewers.push(s.user);
        }
    }

    // notify
    io.to(room).emit("doc_viewers", {
        doctype: args.doctype,
        docname: args.docname,
        viewers: viewers
    });
}

/**
 *
 * THE CODE ABOVE IS COPIED FROM FRAPPE
 *
 */

function getRenovationUserDetails(socket) {
    return new Promise((resolve, rej) => {
        const headers = {
            'X-Client-Site': get_site_name(socket),
            'Accept': 'application/json'
        }

        const query = {};
        if (socket.request.headers.cookie) {
            query.sid = cookie.parse(socket.request.headers.cookie).sid
        }

        if (socket.request.headers.authorization) {
            // Sending auth token both in header and in query param due to inconsistent behaviour observed
            // This ensures that somehow the token gets to the server and is validated for appropriate response
            headers["Authorization"] = socket.request.headers.authorization;
            query.token = getJwtToken(socket);
        }

        request.get(get_url(socket, '/api/method/renovation_core.realtime.get_user_info'))
            .set(headers)
            .type('form')
            .query(query)
            .end(function (err, res) {
                let result = {
                    user: "Guest",
                    sid: "Guest"
                };
                if (err) {
                    console.log(err);
                    return {}
                }
                if (res.status == 200) {
                    result = res.body.message;
                }
                resolve(result);
            });
    });
}

function getJwtToken(socket) {
    const auth = socket.request.headers.authorization;
    if (auth && typeof (auth) === "string") {
        const d = auth.split(" ");
        if (d[0].toLowerCase().indexOf("jwt") >= 0) {
            return d[1];
        }
    }
    return null;
}