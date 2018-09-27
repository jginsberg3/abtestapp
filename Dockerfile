FROM continuumio/miniconda3

# copy the environment.yml file to the docker image tmp directory
ADD environment.yml /tmp/environment.yml
# create the environment
RUN conda env create -f /tmp/environment.yml

# add the command to activate environment to your bashrc
RUN echo "source activate abtestapp" > ~/.bashrc
# add the env to your path or something (i don't really know what this does)
ENV PATH /opt/conda/envs/abtestapp/bin:$PATH

# copy the application.py file to the docker image opt directory
ADD application.py /application.py

# run the app with gunicorn
# bind it to the port you will pass in via the command line when you start the container
# the $PORT variable is required for Heroku deployment
CMD gunicorn -b 0.0.0.0:$PORT application:application
