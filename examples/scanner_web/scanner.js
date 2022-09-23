let websocket;
let pcm_player;


function create_table_row(freq, tg, icon, user, source)
{
    const table_row = document.createElement("div");
    table_row.className = "scanner_rowgroup";
    table_row.id = freq;

    // create frequency column
    const freq_column = document.createElement("div");
    let freq_string = (freq / 1e6).toFixed(4) + " MHz";
    freq_column.className = "scanner_col0 scanner_cell_frequency";
    freq_column.textContent = freq_string;

    // create TG column
    const tg_column = document.createElement("div");
    tg_column.className = "scanner_col1";
    tg_column.textContent = tg;

    // create class icon column
    const icon_column = document.createElement("div");
    icon_column.className = "scanner_col2 scanner_cell_category";
    icon_column.textContent = icon;

    // create user column
    const user_column = document.createElement("div");
    user_column.className = "scanner_col3"
    user_column.textContent = user;

    // create source column
    const source_column = document.createElement("div");
    source_column.className = "scanner_col4";
    source_column.textContent = source.toString(16);

    // add column divs to rowgroup
    table_row.append(freq_column, tg_column, icon_column, user_column, source_column);

    return table_row;
}

function create_row_pulldown(freq)
{
    const pulldown_row = document.createElement("div");
    pulldown_row.className = "scanner_rowgroup";
    pulldown_row.id = `pulldown_${freq}`;

    const pulldown_contents = document.createElement("div");
    pulldown_contents.className = "scanner_pulldown";

    const pulldown_hold_group = document.createElement("button");
    //const pulldown_hold_group = document.createElement("div");
    const pulldown_hold_group_enabled_selector = `#pulldown_${freq}_hold_group:enabled`;
    pulldown_hold_group.id = `pulldown_${freq}_hold_group`;
    pulldown_hold_group.className = "scanner_pd_button";
    pulldown_hold_group.textContent = "HOLD GROUP";
    pulldown_hold_group.setAttribute("disabled", "");
    $(document).on("click", pulldown_hold_group_enabled_selector, function() {
        const click_msg = {
            "event": "CLICK_BUTTON",
            "button": "hold_group",
            "freq": freq
        };
        websocket.send(JSON.stringify(click_msg));
    });

    const pulldown_lo_group = document.createElement("button");
    //const pulldown_lo_group = document.createElement("div");
    pulldown_lo_group.id = `pulldown_${freq}_lo_group`;
    const pulldown_lo_group_enabled_selector = `#pulldown_${freq}_lo_group:enabled`;
    pulldown_lo_group.className = "scanner_pd_button";
    pulldown_lo_group.textContent = "L/O GROUP";
    $(document).on("click", pulldown_lo_group_enabled_selector, function() {
        const click_msg = {
            "event": "CLICK_BUTTON",
            "button": "lo_group",
            "freq": freq
        };
        websocket.send(JSON.stringify(click_msg));
    });

    const pulldown_group_prio = document.createElement("button");
    //const pulldown_group_prio = document.createElement("div");
    const pulldown_group_prio_enabled_selector = `#pulldown_${freq}_group_prio:enabled`;
    pulldown_group_prio.id = `pulldown_${freq}_group_prio`;
    pulldown_group_prio.className = "scanner_pd_button";
    pulldown_group_prio.textContent = "GROUP PRIO";
    $(document).on("click", pulldown_group_prio_enabled_selector, function() {
        const click_msg = {
            "event": "CLICK_BUTTON",
            "button": "group_prio",
            "freq": freq
        };
        websocket.send(JSON.stringify(click_msg));
    });

    pulldown_contents.append(pulldown_hold_group, pulldown_lo_group, pulldown_group_prio);

    pulldown_row.append(pulldown_contents);
    return pulldown_row;
}

function add_class(selector, class_to_add)
{
    if(!$(selector).hasClass(class_to_add)) {
        $(selector).addClass(class_to_add);
    }
}

function remove_class(selector, class_to_remove)
{
    if($(selector).hasClass(class_to_remove)) {
        $(selector).removeClass(class_to_remove);
    }
}

function update_row(fields)
{
	let freq_table = document.getElementById("system_table");

    // See if this table row exists on the page
    const selector = `#${fields.freq}`;
    const pulldown_selector = `#pulldown_${fields.freq}`;

    let table_row = document.getElementById(fields.freq);
    if(table_row == null) {
        // No, create the row and the pulldown for the row
        const new_table_row = create_table_row(
            fields.freq, fields.tg, fields.icon, fields.description, fields.source, fields.prio);
        const new_row_pulldown = create_row_pulldown(fields.freq);

        new_table_row.onclick = function() {
            // send Websockets message that a row was clicked
            const click_msg = {
                "event": "CLICK_ROW",
                "freq": fields.freq
            };
            websocket.send(JSON.stringify(click_msg));
        }

        // Insert the row into the right spot in the DOM
        let row_added = false;
        let num_children = freq_table.children.length;
        for (let i = 0; i < num_children; i++) {
            const child_id = freq_table.children[i].id;
            if (!child_id.startsWith("pulldown") && (fields.freq < child_id)) {
                freq_table.insertBefore(new_row_pulldown, freq_table.children[i]);
                freq_table.insertBefore(new_table_row, new_row_pulldown);
                $(pulldown_selector).hide();
                row_added = true;
                break;
            }
        }
        if(!row_added) {
            freq_table.append(new_table_row);
            freq_table.append(new_row_pulldown);
            $(pulldown_selector).hide();
        }
    }
    else {
        // The row exists in the DOM, so update its data
        table_row.children[1].textContent = fields.tg;
        table_row.children[2].textContent = fields.icon;
        table_row.children[3].textContent = fields.description;
        table_row.children[4].textContent = fields.source.toString(16);
    }

    // Update row colors
    let color_set = false;
    if(fields.control) {
        add_class(selector, "scanner_rowgroup_cc_color");
    }
    else {
        if(fields.lockout) {
            add_class(selector, "scanner_rowgroup_lo_color");
            add_class(pulldown_selector, "scanner_rowgroup_lo_color");
            color_set = true;
        }
        else {
            remove_class(selector, "scanner_rowgroup_lo_color");
            remove_class(pulldown_selector, "scanner_rowgroup_lo_color");
        }
        if(fields.playing) {
            add_class(selector, "scanner_rowgroup_playing_color");
            add_class(pulldown_selector, "scanner_rowgroup_playing_color");
            color_set = true;
        }
        else {
            remove_class(selector, "scanner_rowgroup_playing_color");
            remove_class(pulldown_selector, "scanner_rowgroup_playing_color");
        }
        if(fields.drawer_open && !color_set) {
            add_class(selector, "scanner_pulldown_open_color");
            add_class(pulldown_selector, "scanner_pulldown_open_color");
        }
        else {
            remove_class(selector, "scanner_pulldown_open_color");
            remove_class(pulldown_selector, "scanner_pulldown_open_color");
        }
    }

    // Update button states
    let lo_selector = `#pulldown_${fields.freq}_lo_group`;
    let group_prio_selector = `#pulldown_${fields.freq}_group_prio`;
    if(fields.active) {
        $(lo_selector).removeAttr("disabled");
        $(group_prio_selector).removeAttr("disabled");
        if(fields.lockout) {
            add_class(lo_selector, "scanner_pd_button_toggled")
        }
        else {
            remove_class(lo_selector, "scanner_pd_button_toggled")
        }
        if(fields.prio) {
            add_class(group_prio_selector, "scanner_pd_button_toggled")
        }
        else {
            remove_class(group_prio_selector, "scanner_pd_button_toggled")
        }
    }
    else {
        $(lo_selector).attr("disabled", "");
        $(group_prio_selector).attr("disabled", "");
        remove_class(lo_selector, "scanner_pd_button_toggled")
        remove_class(group_prio_selector, "scanner_pd_button_toggled")
    }
}

function update_heartbeat(display)
{
	let hb_div = document.getElementById("cc_status");
    hb_div.textContent = display;
}

function update_cc_quality(display)
{
	let cc_qual = document.getElementById("cc_quality");
    cc_qual.textContent = display;
}

function update_tc_quality(display)
{
	let tc_qual = document.getElementById("tc_quality");
    tc_qual.textContent = display;
}

function show_row_buttons(freq)
{
    let table_row = document.getElementById(freq);
    selector = "#pulldown_" + freq;
    if(table_row != null) {
        $(selector).show();
    }
}

function hide_row_buttons(freq)
{
    let table_row = document.getElementById(freq);
    selector = "#pulldown_" + freq;
    if(table_row != null) {
        $(selector).hide();
    }
}

function handle_pcm_data(data)
{
    var pcm_data = new Uint8Array(data);
    if(pcm_player != null) {
        pcm_player.feed(pcm_data);
    }
}

function handle_json_data(data)
{
    const message = JSON.parse(data);
    console.log(message);
    if(message.event == "UPDATE_ROW") {
        update_row(message);
    }
    if(message.event == "UPDATE_HEARTBEAT") {
        update_heartbeat(message.display);
    }
    if(message.event == "UPDATE_CC_QUALITY") {
        update_cc_quality(message.display);
    }
    if(message.event == "UPDATE_TC_QUALITY") {
        update_tc_quality(message.display);
    }
    if(message.event == "SHOW_ROW_BUTTONS") {
        show_row_buttons(message.freq);
    }
    if(message.event == "HIDE_ROW_BUTTONS") {
        hide_row_buttons(message.freq);
    }
}

window.addEventListener("DOMContentLoaded", () => {
	websocket = new WebSocket("ws://" + location.hostname + ":8001/");
    websocket.binaryType = "arraybuffer";
	websocket.addEventListener("message", ({data}) => {
        if(data instanceof ArrayBuffer) {
            handle_pcm_data(data);
        }
        else {
            handle_json_data(data);
        }
	});
    pcm_player = new PCMPlayer({
        encoding: '16bitInt',
        channels: 1,
        sampleRate: 8000,
        flushingTime: 250
    });
	//websocket.addEventListener("open", () => {
	//	const get_tgs = {
	//		"event": "GET_SYSTEM_INFO_TGS"
	//	};
	//	websocket.send(JSON.stringify(get_tgs));
	//});
});
