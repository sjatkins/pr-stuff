#!/usr/bin/ruby -w
puts 'running pr from inside ruby'
#require 'Pathname'
#path = Pathname.new(__FILE__)
#root = File.dirname(path.realpath)
#puts "root = "+root
require "#{Dir.pwd}/pr"
Pr.game_loop