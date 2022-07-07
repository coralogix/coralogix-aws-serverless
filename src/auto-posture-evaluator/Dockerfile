FROM python:3.8

RUN mkdir /auto_posture_evaluator
COPY ./auto_posture_evaluator.py /auto_posture_evaluator/
COPY ./interfaces.py /auto_posture_evaluator/
COPY ./lambda_function.py /auto_posture_evaluator/
COPY /testers /auto_posture_evaluator/testers
COPY /model /auto_posture_evaluator/model
COPY ./requirements.txt /auto_posture_evaluator/

RUN pip3 install -r /auto_posture_evaluator/requirements.txt
RUN chmod +x /auto_posture_evaluator/lambda_function.py
WORKDIR /auto_posture_evaluator
CMD ["/auto_posture_evaluator/lambda_function.py"]
