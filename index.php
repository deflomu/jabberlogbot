<html>

<head>

<title>Jabber Log</title>

<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />

<style type="text/css">
body {
    font-family: Verdana, Helvetica, sans-serif;
    font-size: 12px;
    color: #000000;
}
.date {
	font-family: Courier New, Courier, mono;
}
pre {
	white-space: pre-wrap;
}
</style>

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
    
<?php
        readfile($date . ".log");
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
