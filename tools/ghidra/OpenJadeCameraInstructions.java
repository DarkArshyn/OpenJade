// Preserve instructions where decompiler signatures hide register arguments.
import ghidra.app.script.GhidraScript;
import java.nio.file.*;
public class OpenJadeCameraInstructions extends GhidraScript {
 public void run() throws Exception {
  if (!"6587d499f4ea6d0895179f74487045bc2c82a9d4e08a0a5046c1fb88ee3b6ec9".equalsIgnoreCase(currentProgram.getExecutableSHA256())) throw new Exception("Hash mismatch");
  StringBuilder out=new StringBuilder();
  for(long base:new long[]{0x729824L,0x438830L,0x438790L}){
   out.append("START ").append(Long.toHexString(base)).append("\n");
   var at=toAddr(base);
   for(int i=0;i<35;i++){var instruction=getInstructionAt(at);if(instruction==null){disassemble(at);instruction=getInstructionAt(at);}if(instruction==null)break;out.append(at).append(" ").append(instruction).append("\n");at=instruction.getMaxAddress().add(1);}
  }
  Files.writeString(Paths.get(getScriptArgs()[0]),out.toString());
 }
}
