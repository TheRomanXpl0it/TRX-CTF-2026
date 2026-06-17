require 'sinatra'
require 'open3'

set :bind, '0.0.0.0'
set :port, 4567

get '/' do
  erb :index
end

post '/lookup' do
  @domain = params[:domain]
  if @domain && @domain.match?(/^[a-z.-]+$/)
    stdout, stderr, status = Open3.capture3("whois #{@domain}")
    @result = stdout.empty? ? stderr : stdout
    @success = status.success?
  else
    @error = "Invalid domain format"
  end
  erb :result
end
