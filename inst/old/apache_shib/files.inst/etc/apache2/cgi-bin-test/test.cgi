#!/usr/bin/perl
use CGI;
print CGI->header;
print "<pre>\n";
for (sort keys %ENV) {
   print "$_ = ", $ENV{$_}, "\n";
}
print "</pre>\n";
exit 0;
