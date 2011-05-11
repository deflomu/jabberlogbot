<html>

<head>

<title>Jabber Log</title>

<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />

<style type="text/css">
body {
    font-family: Verdana, Arial, Helvetica, sans-serif;
    font-size: 12px;
}
table {
	font-size: 1.1em;
}
.date  {
	vertical-align: top;
}
.message {
	white-space: pre-wrap;
}
.nick {
	vertical-align: top;
	text-align: right;
	padding: 0 1em;
}
</style>

<script type="text/javascript" src="http://github.com/cowboy/javascript-linkify/raw/master/ba-linkify.min.js"></script>
<script type="text/javascript" src="http://ajax.googleapis.com/ajax/libs/jquery/1.4.2/jquery.min.js"></script>
<script type="text/javascript">
function colorFromString(str, seed) { // java String#hashCode
	var hash = seed;
	for (var i = 0; i < str.length; i++) {
		hash = str.charCodeAt(i) + ((hash << 5) - hash);
	}
	var color = Math.abs(hash).toString(16).substring(0,6);
	return color;
} 

$(document).ready(function()
{
	var seed = parseInt(Math.random()*100);
	$("#logtable tr").each(function() {
		var nick = $(this).find("td:nth-child(2)");
		var color = colorFromString(nick.html(), seed);
		nick.css("color", color);

		var message = $(this).find("td:nth-child(3)");

		linkifyoptions = {
			callback: function( text, href ) {
        			return href ? '<a target="_blank" href="' + href + '" title="' + href + '">' + text + '</a>' : text;
			}
		};
		message.html(linkify(message.html(), linkifyoptions));
	});
});
</script>

</head>

<body>

<h1>Jabber Logs for <?php 
$dir = explode("/",getcwd());
echo $dir[sizeof($dir)-1]; ?></h1>
<?php

    $date = $_GET['date'];
    if (isset($date) && preg_match("/^\d\d\d\d-\d\d-\d\d$/", $date)) {
?>

    <p>
     <a href="./">Index</a>
    </p>

    <h2><?php echo($date); ?></h2>
    <table id="logtable">
	<tbody>
<?php
        readfile($date . ".log");
?>
	</tbody>
    </table>
<?php
    }
    else {
        $dir = opendir(".");
        while (false !== ($file = readdir($dir))) {
            if (strpos($file, ".log") == 10) {
                $filearray[] = $file;
            }
        }
        closedir($dir);
        
        rsort($filearray);
?>
	<h2>Available Logs</h2>
    <ul>
<?php
        
        
        foreach ($filearray as $file) {
            $file = substr($file, 0, 10);
?>
        <li><a href="<?php echo($_SERVER['PHP_SELF'] . "?date=" . $file); ?>"><?php echo($file); ?></a></li>
<?php
        }
?>
    </ul>
<?php
    }
?>
</body>
</html>
