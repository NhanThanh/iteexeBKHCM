# ===========================================================================
# eXe 
# Copyright 2004-2006, University of Auckland
# Copyright 2004-2008 eXe Project, http://eXeLearning.org
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
# ===========================================================================
"""
QuizTestBlock can render and process QuizTestIdevices as XHTML
"""

import logging
from exe.webui.block                 import Block
from exe.webui.testquestionelement   import TestquestionElement
from exe.webui                       import common
log = logging.getLogger(__name__)


# ===========================================================================
class QuizTestBlock(Block):
    """
    QuizTestBlock can render and process QuizTestIdevices as XHTML
    """
    def __init__(self, parent, idevice):
        """
        Initialize a new Block object
        """
        Block.__init__(self, parent, idevice)
        self.idevice           = idevice
        self.questionElements  = []
        self.message = False
        self.allQuizTitles = []
        if not hasattr(self.idevice,'undo'): 
            self.idevice.undo = True

        i = 0
        for question in idevice.questions:
            self.questionElements.append(TestquestionElement(i, idevice, 
                                                             question))
            i += 1

    def process(self, request):
        """
        Process the request arguments from the web server
        """
        Block.process(self, request)
        
        is_cancel = common.requestHasCancel(request)
            
        if ("addQuestion"+unicode(self.id)) in request.args: 
            self.idevice.addQuestion()
            self.idevice.edit = True
            # disable Undo once a question has been added: 
            self.idevice.undo = False
            
        if "passrate" in request.args \
        and not is_cancel:
            self.idevice.passRate = request.args["passrate"][0]


        for element in self.questionElements:
            element.process(request)

            
        if ("action" in request.args and request.args["action"][0] == "done"
            or not self.idevice.edit):
            self.idevice.isAnswered = True
            # remove the undo flag in order to reenable it next time:
            if hasattr(self.idevice,'undo'): 
                del self.idevice.undo
            for question in self.idevice.questions:
                if not question.isHard and not question.isMedium and not question.isEasy:
                    self.idevice.isSetDiff = False
                    self.idevice.edit = True
                    break
                if question.correctAns == -2:
                    self.idevice.isAnswered = False
                    self.idevice.edit = True
                    break
            
        if "submitScore" in request.args \
        and not is_cancel:
            self.idevice.score = self.__calcScore()
            
        if "title"+self.id in request.args \
        and not is_cancel:
            self.idevice.title = request.args["title"+self.id][0]
            

    def renderEdit(self, style):
        """
        Returns an XHTML string with the form element for editing this block
        """
        html  = "<div class=\"iDevice\">\n"
        if not self.idevice.isAnswered:
            html += common.editModeHeading(
                _("Please select a correct answer for each question."))

        if not self.idevice.isSetDiff:
            html += common.editModeHeading(
                _("Please select a Difficulty level for all Quiz"))

        self.allQuizTitles = []
        self.__getAllQuizTitles(self.package.root, 0)

        if self.allQuizTitles.count(self.idevice.title) != 1:
            html += common.editModeHeading(
                _("PLease change the Quiz title, Title must be unique."))
        html += common.textInput("title"+self.id, self.idevice.title)
        html += u"<br/><br/>\n"
        

        for element in self.questionElements:
            html += element.renderEdit() 
            
        value = _("Add another Question")    
        html += "<br/>" 
        html += common.submitButton("addQuestion"+unicode(self.id), value)
        html += "<br/><br/>" +  _("Select pass rate: ")
        html += "<select name=\"passrate\">\n"
        template = '  <option value="%s0"%s>%s0%%</option>\n'
        for i in range(1, 11):
            if str(i)+ "0" == self.idevice.passRate:
                html += template % (str(i), ' selected="selected"', str(i))
            else:
                html += template % (str(i), '', str(i))
        html += "</select>\n"
        html += "<br /><br />" + self.renderEditButtons(undo=self.idevice.undo)
        html += "</div>\n"
        self.idevice.isAnswered = True

        return html

    def __getAllQuizTitles(self, Rooot, depth):
        for idevice in Rooot.idevices:
            if  hasattr(idevice, "isQuiz"):
                self.allQuizTitles.append(idevice._title)
        for child in Rooot.children:
            self.__getAllQuizTitles(child, depth + 1)
        return True

    def renderView(self, style, preview=False, numQ=None):
        """
        Returns an XHTML string for viewing this block
        """
        lb = "\n" #Line breaks
        html = common.ideviceHeader(self, style, "view")
        html += '<form name="quizForm%s" id="quizForm%s" action="javascript:calcScore2();">' % (self.idevice.id, self.idevice.id)
        html += lb
        html += u'<input type="hidden" name="passrate" id="passrate-'+self.idevice.id+'" value="'+self.idevice.passRate+'" />'+lb
        for element in self.questionElements:
            if preview: 
                html += element.renderPreview()
            else:
                html += element.renderView()
        html += '<div class="block iDevice_buttons">'+lb
        html += '<p><input type="submit" name="submitB" value="' + c_("SUBMIT ANSWERS")+ '"  onclick="calcScore2%s()" /> '%numQ + '</p>'+lb
        html += '</div>'+lb 
        html += '<div id="quizFormScore'+self.id+'"></div>'+lb
        html += '</form>'+lb
        html += common.ideviceFooter(self, style, "view")
        return html

    def renderJavascriptForWeb(self):
        """
        Return an XHTML string for generating the javascript for web export
        """
        scriptStr  = '<script type="text/javascript">/*<![CDATA[*/'
        scriptStr += '\n'
        scriptStr += "var numQuestions = " 
        scriptStr += str(len(self.questionElements))+";\n"
        scriptStr += "var rawScore = 0;\n" 
        scriptStr += "var actualScore = 0;\n"
        answerStr  = """function getAnswer()
        {"""
        varStrs     = ""
        keyStrs     = ""
        answers     = ""
        rawScoreStr = """}
        function calcRawScore(){\n"""
        
        for element in self.questionElements:
            i = element.index
            varStr    = "question" + str(i)
            keyStr    = "key" + str(i)
            quesId    = "key" + str(element.index) + "b" + self.id
            numOption = element.getNumOption()
            answers  += "var key"  + str(i) + " = " 
            answers  += str(element.question.correctAns) + ";\n"
            getEle    = 'document.getElementById("quizForm%s")' % \
                        self.idevice.id
            chk       = '%s.%s[i].checked'% (getEle, quesId)
            value     = '%s.%s[i].value' % (getEle, quesId)
            varStrs += "var " + varStr + ";\n"
            keyStrs += "var key" + str(i)+ " = " 
            keyStrs += str(element.question.correctAns) + ";\n"   
            
            answerStr += """
            for (var i=0; i < %s; i++)
            {
               if (%s)
               {
                  %s = %s;
                  break;
               }
            }
            """ % (numOption, chk, varStr, value) 
            
            rawScoreStr += """
            if (%s == %s)
            {
               rawScore++;
            }""" % (varStr, keyStr)
            
        scriptStr += varStrs       
        scriptStr += keyStrs
        
        scriptStr += answerStr 
                        
        scriptStr += rawScoreStr 
        
        scriptStr += """
        
        }
        
        function calcScore2()
        {
            getAnswer();
     
            calcRawScore();
            actualScore =  Math.round(rawScore / numQuestions * 100);
            var id = "%s";
            document.getElementById("quizForm"+id).submitB.disabled = true;
            var s = document.getElementById("quizFormScore"+id);
            """ % self.idevice.id
        scriptStr += '            var msg_str ="' + c_("Your score is %d%%") + '";'
        scriptStr += '            msg_str = msg_str.replace("%d",actualScore).replace("%%","%");'
        scriptStr += '            if (s) { s.innerHTML = "<div class=\'feedback\'><p>"+msg_str+"</p></div>"; } else { alert(msg_str); }'

        scriptStr += """
           
        }
    /*]]>*/</script>\n"""

        return scriptStr

    
    def renderJavascriptForScorm(self, thisnode = None, numQ = None):
        """
        Return an XHTML string for gene rating the javascript for scorm export
        """

        scriptStr  = '<script type="text/javascript">\n'
        scriptStr += '<!-- //<![CDATA[\n'
        scriptStr += "var numQuestions" + str(numQ) +"= "
        scriptStr += unicode(len(self.questionElements))+";\n"
        scriptStr += "var rawScore" + str(numQ) +" = 0;\n"
        scriptStr += "var actualScore" + str(numQ) +" = 0;\n"
        scriptStr += "var passMode = " + str(thisnode.passMode) +";\n"
        scriptStr += "var passQuiz"+str(numQ)+" = false;\n"
        answerStr  = """function getAnswer%s()
        {"""%numQ
        varStrs     = ""
        keyStrs     = ""
        answers     = ""
        rawScoreStr = """}
        function calcRawScore%s(){\n"""%numQ

        for element in self.questionElements:
            i = element.index
            varStr    = "question" + unicode(i) + str(numQ)
            keyStr    = "key" + unicode(i) + str(numQ)
            quesId    = "key" + unicode(element.index) + "b" + self.id
            numOption = element.getNumOption()
            answers  += "var key"  + unicode(i) +  str(numQ)  + " = "
            answers  += unicode(element.question.correctAns) + ";\n"
            getEle    = 'document.getElementById("quizForm%s")' %self.idevice.id
            chk       = '%s.%s[i].checked'% (getEle, quesId)
            value     = '%s.%s[i].value' % (getEle, quesId)
            varStrs += "var " + varStr + ";\n"
            keyStrs += "var key" + unicode(i) + str(numQ) + " = "
            keyStrs += unicode(element.question.correctAns) + ";\n"          
            answerStr += """
            scorm.SetInteractionValue("cmi.interactions.%s.id","%s");
            scorm.SetInteractionValue("cmi.interactions.%s.type","choice");
            scorm.SetInteractionValue("cmi.interactions.%s.correct_responses.0.pattern",
                          "%s");
            """ % (unicode(i), quesId, unicode(i), unicode(i),
                   element.question.correctAns)
            answerStr += """
            for (var i=0; i < %s; i++)
            {
               if (%s)
               {
                  %s = %s;
                  scorm.SetInteractionValue("cmi.interactions.%s.student_response",%s);
                  break;
               }
            }
           """ % (numOption, chk, varStr, value, unicode(i), varStr)
            rawScoreStr += """
            if (%s == %s)
            {
               scorm.SetInteractionValue("cmi.interactions.%s.result","correct");
               rawScore%s++;
            }
            else
            {
               scorm.SetInteractionValue("cmi.interactions.%s.result","wrong");
            }""" % (varStr , keyStr, unicode(i), numQ, unicode(i))
           
        scriptStr += varStrs      
        scriptStr += keyStrs
        scriptStr += answerStr
        scriptStr += rawScoreStr
        scriptStr += """
        }
       
        function calcScore2%s()
        {
           computeTime();  // the student has stopped here.
       """%numQ
        scriptStr += """
           document.getElementById("quizForm%s").submitB.disabled = true;
       """ % (self.idevice.id)
        scriptStr += """
           getAnswer%s();
    
           calcRawScore%s();
          
           actualScore%s = Math.round(rawScore%s / numQuestions%s * 100);
        """%(numQ, numQ, numQ, numQ, numQ)

        scriptStr += '''\n
        submsg = "";
                
                if (actualScore%s < %s){
                submsg += ", Pass rate is %s, You Fail the Quzi";
                passQuiz%s = false;
                }
                else{
                submsg += ", You pass the Quiz";
                passQuiz%s = true;
                }
               ''' % (numQ, self.idevice.passRate, self.idevice.passRate, numQ, numQ)

        tempnum =   'actualScore%s'%(numQ)

        scriptStr += 'var msg_str ="' + c_("Your score is %d%%") + '";\n'
        scriptStr += ' alert(msg_str.replace("%d",' +tempnum+').replace("%%","%") + submsg);\n'


        scriptStr +="""calPass();\n
        
        }"""

        andCon = ""
        orCon =  ""
        for i in range(len(thisnode.quiztoPass)):
            if i== len(thisnode.quiztoPass)-1:
                orCon += "passQuiz%s"%thisnode.quiztoPass[i]
                andCon += "passQuiz%s"%thisnode.quiztoPass[i]
            else:
                orCon += "passQuiz%s"%thisnode.quiztoPass[i] + "|| "
                andCon += "passQuiz%s"%thisnode.quiztoPass[i] + "& "

        if thisnode.passMode == 0:
            scriptStr+="""
            function calPass(){
    if(passMode == 0){//mode Some
 
      if(%s){
          scorm.SetCompletionStatus("completed");
          scorm.SetSuccessStatus("passed");
          scorm.SetExit("");
          exitPageStatus = true;
          scorm.save();
          scorm.quit();
        }}}
            """%andCon
        elif thisnode.passMode == 1:
            scriptStr+="""
  function calPass(){
    if(passMode == 1){//mode ANY
      if(%s){
        scorm.SetCompletionStatus("completed");
        scorm.SetSuccessStatus("passed");
        scorm.SetExit("");
        exitPageStatus = true;
        scorm.save();
        scorm.quit();
      }}}\n"""%orCon
        else:
            scriptStr+="""
            function calPass(){
    if(passMode == 2){//mode ANY
    
        scorm.SetCompletionStatus("completed");
        scorm.SetSuccessStatus("passed");
        scorm.SetExit("");
        exitPageStatus = true;
        scorm.save();
        scorm.quit();
      }
    }
            """

        scriptStr +="""
//]]> -->
</script>\n"""

        return scriptStr

    def renderPreview(self, style):
        """
        Returns an XHTML string for previewing this block
        """
        lb = "\n" #Line breaks
        html = common.ideviceHeader(self, style, "preview")
        
        html += u'<input type="hidden" name="passrate" id="passrate-'+self.idevice.id+'" value="'+self.idevice.passRate+'" />'
        
        for element in self.questionElements:
            html += element.renderPreview()
        
        html += '<div class="block iDevice_buttons">'+lb
        html += '<p><input type="submit" name="submitScore" value="' + c_("SUBMIT ANSWERS")+'" /></p>'
        html += '</div>'+lb
        
        if not self.idevice.score == -1:
            message = c_("Your score is %d%%")%self.idevice.score
            html += '<script type="text/javascript">alert("'+ message+ '")</script>'

        self.idevice.score = -1   
        
        html += common.ideviceFooter(self, style, "preview")
        
        return html
    

    def __calcScore(self):
        """
        Return a score for preview mode.
        """
        rawScore = 0
        numQuestion = len(self.questionElements)
        score = 0

        for question in self.idevice.questions:
            if (question.userAns == question.correctAns):
                log.info("userAns " +unicode(question.userAns) + ": " 
                         + "correctans " +unicode(question.correctAns))
                rawScore += 1
        
        if numQuestion > 0:
            score = rawScore * 100 / numQuestion
            
        for question in self.idevice.questions:
            question.userAns = -1
            
        return score 
            

# ===========================================================================
"""Register this block with the BlockFactory"""
from exe.engine.quiztestidevice  import QuizTestIdevice
from exe.webui.blockfactory      import g_blockFactory
g_blockFactory.registerBlockType(QuizTestBlock, QuizTestIdevice)    


# ===========================================================================
